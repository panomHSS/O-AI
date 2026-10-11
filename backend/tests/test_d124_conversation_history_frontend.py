"""Execute the actual TypeScript client and Chat handlers with deferred reads.

Uses the existing frontend TypeScript/Node installation; no test dependency is added.
The small hook harness tests state transitions, not browser rendering or React timing.
"""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
PRELUDE = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('./frontend/node_modules/typescript');
function load(path, imports, transform = s => s) {
  const source = transform(fs.readFileSync(path, 'utf8'));
  const js = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2020,
  }}).outputText;
  const exports = {};
  new Function('require', 'exports', js)(name => {
    if (!(name in imports)) throw new Error('Unexpected import: ' + name);
    return imports[name];
  }, exports);
  return exports;
}
const saved = new Map();
global.window = {
  setTimeout, clearTimeout, location: {search: ''},
  history: {replaceState() {}},
  localStorage: {
    getItem: key => saved.get(key) ?? null,
    setItem: (key, value) => saved.set(key, value),
    removeItem: key => saved.delete(key),
  },
};
const api = load('frontend/lib/api-client.ts', {
  '../types/workspace': {parseWorkspaceId: x => ['personal', 'company'].includes(x) ? x : null},
});
const requests = [];
let responseData;
global.fetch = async (url, options) => {
  requests.push({url, options});
  return {ok: true, json: async () => ({success: true, data: responseData})};
};
const key = workspace => `oai.activeConversationId.${workspace}`;
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {resolve = a; reject = b;});
  return {promise, resolve, reject};
};
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
const detail = (id, project_id = null) => ({
  workspace_id: 'personal', id, project_id,
  messages: [{id: 'm-' + id, role: 'assistant', content: id,
    citations: [{citation_id: 'citation'}], context_usage: {total_items: 1},
    action: {id: 'must-not-replay'}}],
});
function mount(workspace = 'personal') {
  const slots = [], effects = [], calls = [], reads = new Map(), projects = new Map();
  let cursor = 0, first = true;
  const mockApi = {
    ApiError: api.ApiError,
    listConversations: async w => {calls.push(['list', w]); return [{id: 'old', workspace_id: w}];},
    getAIBrainCapabilities: async () => ({tasks: []}),
    getConversation: (w, id) => {calls.push(['detail', w, id]); return reads.get(id).promise;},
    getProject: (w, id) => {calls.push(['project', w, id]); return projects.get(id).promise;},
    sendChatMessage: () => {throw new Error('History must not invoke Chat');},
  };
  const react = {
    useState(initial) {
      const i = cursor++;
      if (first) slots[i] = initial;
      return [slots[i], value => {slots[i] = typeof value === 'function' ? value(slots[i]) : value;}];
    },
    useRef(initial) {
      const i = cursor++;
      if (first) slots[i] = {current: initial};
      return slots[i];
    },
    useCallback: fn => fn,
    useEffect: fn => {if (first) effects.push(fn);},
  };
  const imports = {
    react, 'react/jsx-runtime': {jsx: (type, props, key) => ({type, props, key}), jsxs: (type, props, key) => ({type, props, key})},
    '../../lib/api-client': mockApi,
    '../../lib/workspace': {activeConversationStorageKey: key},
    '../workspace/workspace-provider': {useWorkspace: () => ({workspaceId: workspace, isReady: true})},
  };
  for (const name of ['action-approval-card', 'calendar-write-approval-card',
    'calendar-delete-selection-card', 'context-usage', 'engineering-owner-panel']) imports['./' + name] = {};
  let state;
  global.__captureD124 = value => {state = value;};
  const {Chat} = load('frontend/components/chat/chat.tsx', imports, source => source.replace(
    '  if (!isWorkspaceReady) {',
    `  globalThis.__captureD124({messages, conversationId, associatedProject, pendingProject,
       draft, error, history, isRestoring, setDraft, setPendingProject, setError,
       handleRestoreConversation, handleNewConversation, refreshHistory});
       if (!isWorkspaceReady) {`));
  const render = () => {cursor = 0; global.__captureD124 = value => {state = value;}; Chat(); first = false; return state;};
  render();
  return {render, calls, reads, projects, effects,
    start: () => effects.map(fn => fn()).filter(Boolean),
  };
}
async function restore(m, id, project = null) {
  const read = deferred(); m.reads.set(id, read);
  m.render().handleRestoreConversation(id);
  read.resolve(detail(id, project)); await flush();
}
"""


def run_js(body: str) -> None:
    node = shutil.which("node")
    assert node, "D124 executable tests require the existing Node installation"
    result = subprocess.run(
        [node, "-e", PRELUDE + "\n(async () => {\n" + body +
         "\n})().catch(error => { console.error(error); process.exitCode = 1; });"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_list_exact_workspace_get_and_server_order() -> None:
    run_js("""
      responseData = [{workspace_id: 'company', id: 'z'}, {workspace_id: 'company', id: 'a'}];
      assert.deepEqual(await api.listConversations('company'), responseData);
      assert.equal(requests.length, 1);
      assert.ok(requests[0].url.endsWith('/conversations'));
      assert.equal(requests[0].options.method, 'GET');
      assert.equal(requests[0].options.headers.get('X-OAI-Workspace'), 'company');
    """)


@pytest.mark.parametrize("workspace,id", [("company", "wanted"), ("personal", "wrong")])
def test_detail_rejects_mismatched_workspace_or_exact_id(workspace: str, id: str) -> None:
    run_js(f"""
      responseData = {{workspace_id: '{workspace}', id: '{id}'}};
      await assert.rejects(api.getConversation('personal', 'wanted'), {{status: 409}});
      assert.equal(requests.length, 1);
    """)


def test_list_rejects_any_mismatched_item_without_retry() -> None:
    run_js("""
      responseData = [{workspace_id: 'personal'}, {workspace_id: 'company'}];
      await assert.rejects(api.listConversations('personal'), {status: 409});
      assert.equal(requests.length, 1);
    """)


def test_history_loading_never_selects_or_executes() -> None:
    run_js("""
      const m = mount(); m.start(); await flush();
      assert.deepEqual(m.calls, [['list', 'personal']]);
      assert.equal(m.render().conversationId, null);
      assert.equal(saved.size, 0);
    """)


def test_project_restore_is_atomic_and_stored_messages_are_display_only() -> None:
    run_js("""
      const m = mount(); await restore(m, 'current');
      m.render().setDraft('unsent'); m.render().setPendingProject({id: 'pending'});
      m.render().setError('stale');
      const project = deferred(); m.projects.set('p', project);
      await restore(m, 'selected', 'p');
      assert.equal(m.render().conversationId, 'current');
      assert.equal(saved.get(key('personal')), 'current');
      assert.deepEqual(m.calls.at(-1), ['project', 'personal', 'p']);
      project.resolve({id: 'p', title: 'Project'}); await flush();
      const s = m.render();
      assert.equal(s.conversationId, 'selected');
      assert.equal(s.associatedProject.id, 'p');
      assert.equal(s.pendingProject, null); assert.equal(s.draft, ''); assert.equal(s.error, null);
      assert.deepEqual(s.messages[0].citations, [{citation_id: 'citation'}]);
      assert.deepEqual(s.messages[0].contextUsage, {total_items: 1});
      assert.equal(s.messages[0].action, undefined);
      assert.equal(saved.get(key('personal')), 'selected');
    """)


@pytest.mark.parametrize("failure", ["detail", "project", "project-id"])
def test_failed_restore_preserves_active_state_and_key(failure: str) -> None:
    run_js("""
      const m = mount(); const initialProject = deferred(); m.projects.set('initial', initialProject);
      initialProject.resolve({id: 'initial'}); await restore(m, 'current', 'initial');
      const before = m.render();
      const read = deferred(), project = deferred();
      m.reads.set('bad', read); m.projects.set('bad-project', project);
      m.render().handleRestoreConversation('bad');
    """ + {
        "detail": "read.reject(new Error('detail unavailable'));",
        "project": "read.resolve(detail('bad', 'bad-project')); await flush(); project.reject(new Error('Project unavailable'));",
        "project-id": "read.resolve(detail('bad', 'bad-project')); await flush(); project.resolve({id: 'wrong'});",
    }[failure] + """
      await flush(); const after = m.render();
      assert.equal(after.conversationId, before.conversationId);
      assert.deepEqual(after.messages, before.messages);
      assert.deepEqual(after.associatedProject, before.associatedProject);
      assert.equal(saved.get(key('personal')), 'current');
      assert.ok(after.error);
    """)


@pytest.mark.parametrize("late", ["detail", "project", "error"])
def test_newer_selection_wins_over_late_results(late: str) -> None:
    run_js("""
      const m = mount(), old = deferred(), project = deferred();
      m.reads.set('old', old); m.projects.set('p', project);
      m.render().handleRestoreConversation('old');
    """ + ("old.resolve(detail('old', 'p')); await flush();" if late == "project" else "") + """
      await restore(m, 'new');
    """ + {
        "detail": "old.resolve(detail('old'));",
        "project": "project.resolve({id: 'p'});",
        "error": "old.reject(new Error('late error'));",
    }[late] + """
      await flush(); assert.equal(m.render().conversationId, 'new');
      assert.equal(m.render().error, null);
      assert.equal(saved.get(key('personal')), 'new');
    """)


def test_new_conversation_cancels_restore_without_deleting_history() -> None:
    run_js("""
      const m = mount(); m.start(); await flush(); await restore(m, 'current');
      saved.set(key('company'), 'company-current');
      const old = deferred(); m.reads.set('old', old);
      m.render().handleRestoreConversation('old');
      const count = m.calls.length; m.render().handleNewConversation();
      old.resolve(detail('old')); await flush();
      const s = m.render(); assert.equal(s.conversationId, null); assert.deepEqual(s.messages, []);
      assert.equal(s.associatedProject, null); assert.equal(s.isRestoring, false);
      assert.equal(saved.has(key('personal')), false);
      assert.equal(saved.get(key('company')), 'company-current');
      assert.equal(s.history.length, 1); assert.equal(m.calls.length, count);
    """)


def test_workspace_unmount_invalidates_pending_restore_and_history() -> None:
    run_js("""
      const personal = mount(); const cleanup = personal.start(); await flush();
      const read = deferred(); personal.reads.set('late', read);
      personal.render().handleRestoreConversation('late');
      const pendingList = personal.render().refreshHistory('personal');
      cleanup.forEach(fn => fn());
      const company = mount('company'); company.start(); await flush();
      read.resolve(detail('late')); await pendingList; await flush();
      assert.equal(company.render().conversationId, null);
      assert.equal(company.render().history[0].workspace_id, 'company');
      assert.equal(saved.size, 0);
    """)


def test_browser_refresh_restores_saved_exact_selection() -> None:
    run_js("""
      const first = mount(); await restore(first, 'selected');
      const second = mount(), read = deferred(); second.reads.set('selected', read);
      second.start(); read.resolve(detail('selected')); await flush();
      assert.equal(second.render().conversationId, 'selected');
      assert.ok(second.calls.some(call => call.join(':') === 'detail:personal:selected'));
    """)
