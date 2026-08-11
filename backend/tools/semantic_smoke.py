from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.dependencies import get_embedding_provider
from app.db.session import create_database_engine
from app.repositories.knowledge import KnowledgeRepository
from app.readers.base import SourceSection
from app.search.postgresql_vector import PostgreSQLVectorSearchAdapter
from app.core.config import get_settings


settings = get_settings()
engine = create_database_engine(
    settings.oai_database_url
)

connection = engine.connect()
transaction = connection.begin()

session = Session(
    bind=connection,
    autoflush=False,
    expire_on_commit=False,
)

try:
    embeddings = get_embedding_provider()

    search = PostgreSQLVectorSearchAdapter(
        session,
        embeddings,
    )

    repository = KnowledgeRepository(
        session=session,
        search=search,
    )

    unique_id = str(uuid4())

    metadata = {
        "source_path": f"smoke/{unique_id}.txt",
        "file_name": "semantic-smoke-test.txt",
        "file_extension": ".txt",
        "mime_type": "text/plain",
        "file_size": 300,
        "content_hash": unique_id.replace("-", "") * 2,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    sections = [
        SourceSection(
            sequence=0,
            text=(
                "A centrifugal pump moves liquid by "
                "converting rotational energy into fluid energy."
            ),
            source_locator="section:pump",
        ),
        SourceSection(
            sequence=1,
            text=(
                "A gearbox changes rotational speed and torque "
                "between a motor and driven equipment."
            ),
            source_locator="section:gearbox",
        ),
        SourceSection(
            sequence=2,
            text=(
                "A boiler produces steam by transferring heat "
                "from combustion to water."
            ),
            source_locator="section:boiler",
        ),
    ]
    
    document = repository.replace_index(
        document=None,
        metadata=metadata,
        sections=sections,
        indexed_at=datetime.now(timezone.utc),
    )

    results = repository.search(
        "Which equipment converts motor rotation "
        "into liquid flow and pressure?",
        limit=3,
    )

    own_results = [
        result
        for result in results
        if result["document_id"] == document.id
    ]

    print("Document =", document.id)
    print("Results =", len(own_results))

    for index, result in enumerate(
        own_results,
        start=1,
    ):
        print(
            index,
            result["source_locator"],
            round(
                float(result["relevance_score"]),
                6,
            ),
        )

    if not own_results:
        raise RuntimeError(
            "Smoke-test document was not retrieved."
        )

    if (
        own_results[0]["source_locator"]
        != "section:pump"
    ):
        raise RuntimeError(
            "Semantic ranking did not place "
            "the pump section first."
        )

    print("Top result = section:pump")
    print("Semantic retrieval = PASS")

finally:
    session.close()

    if transaction.is_active:
        transaction.rollback()

    connection.close()
    engine.dispose()

    print("Transaction = ROLLED BACK")
