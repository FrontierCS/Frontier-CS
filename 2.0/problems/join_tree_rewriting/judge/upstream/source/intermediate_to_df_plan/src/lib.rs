use std::{error::Error, fs::File, io::BufReader, path::Path, sync::Arc, time::Duration};

use datafusion::{
    arrow::array::RecordBatch,
    error::DataFusionError,
    execution::TaskContext,
    physical_plan::{collect, ExecutionPlan},
};
use intermediate_plan::Plan;
use to_execution_plan::ToPhysicalNode;
use util::Catalog;

pub mod intermediate_plan;
pub mod to_execution_plan;
pub mod util;

/// Convert a query plan from its IR representation to an [ExecutionPlan].
pub async fn to_execution_plan(
    path: &Path,
    catalog: &mut Catalog,
    alternative_flatten: bool,
) -> Result<Arc<dyn ExecutionPlan>, Box<dyn Error>> {
    // Open the file
    let file = File::open(&path)?;
    let reader = BufReader::new(file);

    // Deserialize the JSON into a Plan struct
    let plan: Plan = serde_json::from_reader(reader)?;
    catalog.update_aliases(&plan);

    // Convert the Plan into an ExecutionPlan
    let (_dfschema, plan) = plan
        .root
        .to_execution_plan(&catalog, alternative_flatten)
        .await?;
    Ok(plan)
}

/// Run the given [ExecutionPlan] and return the time taken to execute it.
pub async fn time_execution(
    plan: Arc<dyn ExecutionPlan>,
    context: Arc<TaskContext>,
) -> Result<(Vec<RecordBatch>, Duration), DataFusionError> {
    let start = std::time::Instant::now();
    let result = collect(plan, context).await?;
    let duration = start.elapsed();
    Ok((result, duration))
}
