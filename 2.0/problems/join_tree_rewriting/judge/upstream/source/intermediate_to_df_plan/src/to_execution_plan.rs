use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
};

use async_recursion::async_recursion;
use async_trait::async_trait;
use datafusion::{
    arrow::datatypes::Schema,
    common::{DFField, DFSchema, DFSchemaRef},
    error::DataFusionError,
    execution::context::ExecutionProps,
    logical_expr::build_join_schema,
    optimizer::{
        analyzer::{type_coercion::TypeCoercion, AnalyzerRule},
        unwrap_cast_in_comparison::UnwrapCastInComparison,
        OptimizerRule,
    },
    physical_expr::create_physical_expr,
    physical_plan::{
        aggregates::{create_aggregate_expr, AggregateExec, PhysicalGroupBy},
        expressions::Column,
        filter::FilterExec,
        joins::{utils::JoinOn, HashJoinExec, SortMergeJoinExec},
        memory::MemoryExec,
        projection::ProjectionExec,
        AggregateExpr, ExecutionPlan, PhysicalExpr,
    },
    prelude::Expr,
    sql::TableReference,
};
use regex::Regex;
use yannakakis_join_implementation::yannakakis::{
    flatten::Flatten, groupby::GroupBy, multisemijoin::MultiSemiJoin,
};

use crate::{
    intermediate_plan::{self, SequentialScanNode},
    util::Catalog,
};

#[async_trait]
pub trait ToPhysicalNode {
    /// Convert the intermediate plan node to a DataFusion [ExecutionPlan].
    /// Returns the qualified output schema and the execution plan.
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError>;
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::Node {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        use intermediate_plan::*;
        match self {
            Node::Aggregate(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::Projection(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::Filter(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::HashJoin(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::MergeJoin(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::SequentialScan(n) => n.to_execution_plan(catalog, alternative_flatten).await,
            Node::Yannakakis(n) => n.to_execution_plan(catalog, alternative_flatten).await,
        }
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::YannakakisNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        async fn groupby_to_plan(
            node: &intermediate_plan::GroupByNode,
            catalog: &Catalog,
            alternative_flatten: bool,
        ) -> Result<(DFSchema, GroupBy), DataFusionError> {
            let (child_schema, child) =
                multisemijoin_to_plan(&node.child, catalog, alternative_flatten).await?;
            let group_on = node.group_on.clone();

            Ok((child_schema, GroupBy::new(child, group_on)))
        }

        #[async_recursion]
        async fn multisemijoin_to_plan(
            node: &intermediate_plan::MultiSemiJoinNode,
            catalog: &Catalog,
            alternative_flatten: bool,
        ) -> Result<(DFSchema, MultiSemiJoin), DataFusionError> {
            let mut schema: DFSchema = DFSchema::empty();
            let (guard_schema, guard) = node
                .guard
                .to_execution_plan(catalog, alternative_flatten)
                .await?;
            schema.merge(&guard_schema);

            let mut children = Vec::with_capacity(node.children.len());
            for child in &node.children {
                let (child_schema, child) =
                    groupby_to_plan(child, catalog, alternative_flatten).await?;
                schema.merge(&child_schema);
                children.push(Arc::new(child));
            }

            Ok((
                schema,
                MultiSemiJoin::new(guard, children, node.equijoin_keys.clone()),
            ))
        }

        let (dfschema, root) =
            multisemijoin_to_plan(&self.root, &catalog, alternative_flatten).await?;

        if alternative_flatten {
            Ok((
                Arc::new(dfschema),
                Arc::new(Flatten::new_alternative(Arc::new(root))),
            ))
        } else {
            Ok((Arc::new(dfschema), Arc::new(Flatten::new(Arc::new(root)))))
        }
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::AggregateNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        use datafusion::physical_plan::aggregates::AggregateMode::*;

        // Convert child node to execution plan
        let child = &self.base.children;
        assert!(child.len() == 1, "AggregateNode must have 1 child");
        let (input_dfschema, child) = child[0]
            .to_execution_plan(catalog, alternative_flatten)
            .await?;
        let input_schema = child.schema();

        // Process 'group by' clause (unsupported for now)
        if self.group_by.is_some() {
            unimplemented!("GROUP BY not supported yet");
        }
        let group_by = PhysicalGroupBy::default(); // assume no GROUP BY

        // Parse aggregate expressions
        let (col_idx, aggr_expr) =
            parse_aggr_exprs(&self.aggregate, &input_dfschema, &input_schema, &catalog).await?;

        let filter_expr = aggr_expr.iter().map(|_| None).collect::<Vec<_>>();
        let order_by_expr = aggr_expr.iter().map(|_| None).collect::<Vec<_>>();
        let aggr_exec = AggregateExec::try_new(
            Single,
            group_by,
            aggr_expr,
            filter_expr,
            order_by_expr,
            child,
            input_schema,
        )?;

        // Output schema (with qualified names!)
        let fields = col_idx
            .iter()
            .map(|&id| input_dfschema.field(id).clone())
            .collect::<Vec<_>>();
        let dfschema = DFSchema::new_with_metadata(fields, input_dfschema.metadata().clone())?;

        Ok((Arc::new(dfschema), Arc::new(aggr_exec)))
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::ProjectionNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        assert!(self.base.children.len() == 1);
        let (input_dfschema, child) = self.base.children[0]
            .to_execution_plan(catalog, alternative_flatten)
            .await?;

        let on = &self
            .on
            .iter()
            .map(|f| f.lowercase_all())
            .collect::<Vec<_>>();

        // Find the indices (and name) of the columns to project
        // Take qualified names into account!!!
        let projection_idx = on
            .iter()
            .map(|f| {
                // find position of field in the child schema
                (
                    index_of_column_by_name(
                        &input_dfschema,
                        f.table_name.as_ref().map(|x| x.as_str()),
                        &f.field_name,
                        catalog.aliases(),
                    ),
                    f,
                )
            })
            .map(|x| match x {
                (Ok(Some(id)), f) => Ok((id, f.field_name.clone())),
                (Ok(None), f) => Err(DataFusionError::Plan(format!(
                    "Projection attribute {:?}.{} not found, valid fields in child schema: {}",
                    f.table_name,
                    f.field_name,
                    input_dfschema.as_ref()
                ))),
                (Err(e), _) => Err(e),
            })
            .collect::<Result<Vec<_>, _>>()?;

        // Create physical expressions for the projections
        let exprs = projection_idx
            .iter()
            .map(|(idx, field_name)| {
                let col: Arc<dyn PhysicalExpr> = Arc::new(Column::new(field_name, *idx));
                (col, field_name.clone())
            })
            .collect::<Vec<_>>();

        let proj = ProjectionExec::try_new(exprs, child)?;

        // Output schema (with qualified names!)
        let fields = projection_idx
            .iter()
            .map(|(id, _)| input_dfschema.field(*id).clone())
            .collect::<Vec<_>>();
        let dfschema = DFSchema::new_with_metadata(fields, input_dfschema.metadata().clone())?;

        Ok((Arc::new(dfschema), Arc::new(proj)))
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::FilterNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        assert!(
            self.base.children.len() == 1,
            "FilterNode must have 1 child"
        );
        let (input_dfschema, input) = self.base.children[0]
            .to_execution_plan(catalog, alternative_flatten)
            .await?;

        let input_arrow_schema = input.schema();

        let condition = where_clause_to_physical_expr(
            &self.condition,
            &input_dfschema,
            input_arrow_schema.as_ref(),
            catalog,
        )
        .await?;

        let filter = FilterExec::try_new(condition, input)?;

        Ok((input_dfschema, Arc::new(filter)))
    }
}

/// Wrapper around `DFSchema::index_of_column_by_name` that first resolves aliases.
/// `name` can be a relation name or an alias.
/// Returns None if column not found.
pub fn index_of_column_by_name(
    schema: &DFSchema,
    qualifier: Option<&str>,
    name: &str,
    aliases: &HashMap<String, String>,
) -> Result<Option<usize>, DataFusionError> {
    let name = name.to_lowercase();
    if let Some(qualifier) = qualifier {
        // First try to find the field with the given qualifier
        let idx = schema.index_of_column_by_name(Some(&TableReference::bare(qualifier)), &name)?;
        if idx.is_some() {
            return Ok(idx);
        } else {
            // No field found with the given qualifier
            // Maybe after resolving the alias?

            if let Some(alias) = aliases.get(qualifier) {
                let idx =
                    schema.index_of_column_by_name(Some(&TableReference::bare(alias)), &name)?;
                if idx.is_some() {
                    return Ok(idx);
                }
            }
        }
    }

    // No qualifier, find field by its unqualified name
    schema.index_of_column_by_name(None, &name)
}

pub fn parse_join_condition(
    condition: &intermediate_plan::JoinOn,
    left_dfschema: &DFSchema,
    right_dfschema: &DFSchema,
    catalog: &Catalog,
) -> Result<JoinOn, DataFusionError> {
    // assume single equijoin condition
    let (left, right) = &condition[0];

    // let condition = JoinCondition::try_from(condition).expect("Invalid join condition");
    let aliases = catalog.aliases();

    // Find the indices of the columns to join
    let left_id = match index_of_column_by_name(
        left_dfschema,
        left.table_name.as_deref(),
        &left.field_name,
        aliases,
    )? {
        Some(id) => id,
        None => {
            return Err(DataFusionError::Plan(format!(
            "Error while parsing left part of join condition {:?}. Field not found: {:?}.{} Valid fields: {}",
            condition,
            left.table_name.as_deref(),
            &left.field_name,
            left_dfschema.to_string()
        )))
        }
    };

    let right_id = match index_of_column_by_name(
        right_dfschema,
        right.table_name.as_deref(),
        &right.field_name,
        aliases,
    )? {
        Some(id) => id,
        None => {
            return Err(DataFusionError::Plan(format!(
            "Error while parsing right part of join condition {:?}. Field not found: {:?}.{} Valid fields: {}",
            condition,
            right.table_name.as_deref(),
            &right.field_name,
            right_dfschema.to_string()
        )))
        }
    };

    let on: JoinOn = vec![(
        Column::new(&left.field_name, left_id),
        Column::new(&right.field_name, right_id),
    )];

    Ok(on)
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::HashJoinNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        let children = &self.base.children;
        assert!(children.len() == 2, "HashJoinNode must have 2 children");

        // in our intermediate representation, the left child is the probe side and the right child is the build side
        // in datafusion, it is the opposite
        let ((left_dfschema, left), (right_dfschema, right)) = (
            children[1]
                .to_execution_plan(catalog, alternative_flatten)
                .await?, // right becomes left
            children[0]
                .to_execution_plan(catalog, alternative_flatten)
                .await?, // left becomes right
        );

        // e.g: "a.id = b.id"
        let join_condition = &self
            .condition
            .iter()
            .map(|(l, r)| (l.lowercase_all(), r.lowercase_all()))
            .collect::<Vec<_>>();
        let on = parse_join_condition(
            join_condition, // join_condition is still in its original form, i.e., left = right
            right_dfschema.as_ref(), // so we must swap left and right here as well
            left_dfschema.as_ref(),
            &catalog,
        )?;
        let on = on.into_iter().map(|(l, r)| (r, l)).collect::<Vec<_>>();

        let join = HashJoinExec::try_new(
            left,  // the 'old' right
            right, // the 'old' left
            on,
            None,
            &datafusion::common::JoinType::Inner,
            datafusion::physical_plan::joins::PartitionMode::CollectLeft,
            false,
        )?;

        let output_schema = build_join_schema(
            left_dfschema.as_ref(),
            right_dfschema.as_ref(),
            &datafusion::common::JoinType::Inner,
        )?;

        Ok((Arc::new(output_schema), Arc::new(join)))
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::MergeJoinNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        let children = &self.base.children;
        assert!(children.len() == 2, "MergeJoinNode must have 2 children");

        let ((left_dfschema, left), (right_dfschema, right)) = (
            children[0]
                .to_execution_plan(catalog, alternative_flatten)
                .await?,
            children[1]
                .to_execution_plan(catalog, alternative_flatten)
                .await?,
        );

        // e.g: "a.id = b.id"
        let join_condition = &self.condition;
        let on = parse_join_condition(
            join_condition,
            left_dfschema.as_ref(),
            right_dfschema.as_ref(),
            &catalog,
        )?;

        let join = SortMergeJoinExec::try_new(
            left,
            right,
            on,
            datafusion::common::JoinType::Inner,
            vec![],
            false,
        )?;

        let output_schema = build_join_schema(
            left_dfschema.as_ref(),
            right_dfschema.as_ref(),
            &datafusion::common::JoinType::Inner,
        )?;

        Ok((Arc::new(output_schema), Arc::new(join)))
    }
}

#[async_trait]
impl ToPhysicalNode for intermediate_plan::SequentialScanNode {
    async fn to_execution_plan(
        &self,
        catalog: &Catalog,
        _alternative_flatten: bool,
    ) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
        // seqscan_to_memoryexec(&self, catalog).await

        let relation = &self.relation.to_lowercase();
        let arrow_schema_original = catalog.schemaof(&relation);

        // 1) COMPUTE QUALIFIED OUTPUT SCHEMA

        // Indices of projection columns
        let mut projection_columns: Vec<usize> = Vec::with_capacity(self.projection.len());

        let df_output_schema_projected = DFSchema::new_with_metadata(
            self.projection
                .iter()
                .map(|f| {
                    let table = f
                        .table_name
                        .as_deref()
                        .expect("Output schema of sequential scan node must be qualified.");

                    let col_id = catalog.idx_of_field(table, &f.field_name);
                    projection_columns.push(col_id);
                    DFField::from_qualified(
                        TableReference::bare(table),
                        arrow_schema_original.field(col_id).clone(),
                    )
                })
                .collect::<Vec<DFField>>(),
            HashMap::new(),
        )?;

        // 2) CREATE EXECUTION PLAN NODE

        let execplan = sequential_scan_to_parquetexec(self, catalog).await?;

        assert_eq!(
            execplan.schema().fields().len(),
            df_output_schema_projected.fields().len(),
            "Computed output schema (DFSchema) not compatible with the actual output schema (ArrowSchema). DFSchema: {}, Schema: {}",
            df_output_schema_projected,
            execplan.schema()
        );

        return Ok((Arc::new(df_output_schema_projected), execplan));
    }
}

async fn _seqscan_to_memoryexec(
    seqscannode: &SequentialScanNode,
    catalog: &Catalog,
) -> Result<(DFSchemaRef, Arc<dyn ExecutionPlan>), DataFusionError> {
    let relation = seqscannode.relation.to_lowercase();
    let data = catalog.get_data(&relation);
    let schema = catalog.schemaof(&relation);

    // Indices of projection columns
    let mut projection_columns: Vec<usize> = Vec::with_capacity(seqscannode.projection.len());

    // Check that the output schema is qualified.
    // Also collect (table, field) pairs for the output schema
    let output_schema = seqscannode
        .projection
        .iter()
        .map(|f| match f.table_name.as_ref() {
            Some(table) => Ok((table, &f.field_name)),
            None => Err(DataFusionError::Plan(
                "Output schema of sequential scan node must be qualified.".to_string(),
            )),
        })
        .collect::<Result<Vec<_>, _>>()?;

    // For each (table, field) pair, get the column index
    // Convert into DFSchema
    let output_schema = output_schema
        .into_iter()
        .map(|(table, field)| {
            let col_id = catalog.idx_of_field(table, field);
            projection_columns.push(col_id);
            DFField::from_qualified(TableReference::bare(table), schema.field(col_id).clone())
        })
        .collect::<Vec<_>>();

    match &seqscannode.opt_filter {
        Some(filter) => {
            // If there is a filter, we need to create a FilterExec node on top of the MemoryExec
            // Because MemoryExec does not support filters
            // Sometimes, the filter uses attributes that are not in the projection
            // we solve these problems as follows:
            //
            // 1) create a memoryexec node that reads all columns
            // 2) create a filterexec node on top of (1)
            // 3) create a projectionexec node on top of (2)

            // STEP 1: create a memoryexec node that reads all columns
            let memexec: Arc<dyn ExecutionPlan> =
                Arc::new(MemoryExec::try_new(&[data.to_vec()], schema, None)?);
            let tableref = output_schema[0].qualifier().unwrap();
            let memexec_dfschema =
                DFSchema::try_from_qualified_schema(tableref, memexec.schema().as_ref())?;

            // STEP 2: create a filterexec node on top of (1)
            let condition = where_clause_to_physical_expr(
                filter,
                &memexec_dfschema,
                memexec.schema().as_ref(),
                catalog,
            )
            .await?;

            let filter = Arc::new(FilterExec::try_new(condition, memexec)?);

            // STEP 3: create a projectionexec node on top of (2)
            // Create physical expressions for the projections
            let exprs = projection_columns
                .iter()
                .zip(output_schema.iter())
                .map(|(idx, field)| {
                    let col: Arc<dyn PhysicalExpr> = Arc::new(Column::new(field.name(), *idx));
                    (col, field.name().clone())
                })
                .collect::<Vec<_>>();

            let proj: Arc<dyn ExecutionPlan> = Arc::new(ProjectionExec::try_new(exprs, filter)?);

            return Ok((
                Arc::new(DFSchema::new_with_metadata(output_schema, HashMap::new())?),
                proj,
            ));
        }
        None => {
            // If there is no filter, we can directly create a MemoryExec node
            let memoryexec = Arc::new(MemoryExec::try_new(
                &[data.to_vec()],
                schema,
                Some(projection_columns),
            )?);
            return Ok((
                Arc::new(DFSchema::new_with_metadata(output_schema, HashMap::new())?),
                memoryexec,
            ));
        }
    }
}

/// Convert a [SequentialScanNode] to a physical [ExecutionPlan]
/// that reads from a Parquet file.
async fn sequential_scan_to_parquetexec(
    node: &SequentialScanNode,
    catalog: &Catalog,
) -> Result<Arc<dyn ExecutionPlan>, DataFusionError> {
    let relation = &node.relation.to_lowercase(); // full relation name

    let projection = &node
        .projection
        .iter()
        .map(|f| f.lowercase_all())
        .collect::<Vec<_>>();

    let projection_str = projection
        .iter()
        .map(|field| field.field_name.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let alias = projection[0]
        .table_name
        .as_ref()
        .expect("Projection in SequentialScan must be qualified.");

    let sql = match &node.opt_filter {
        Some(filter) => {
            format!(
                "SELECT {} FROM {} as {} WHERE {}",
                projection_str, relation, alias, filter
            )
        }
        None => format!("SELECT {} FROM {} as {}", projection_str, relation, alias),
    };

    let state = catalog.get_state();
    let plan = state.create_logical_plan(&sql).await?;

    // Optimize plan and convert to physical plan
    let plan = state.create_physical_plan(&plan).await?;

    Ok(plan)
}

/// Parse a SQL WHERE clause into a logical filter expression.
async fn where_clause_to_logical_expr(
    where_clause: &str,
    input_dfschema: &DFSchema,
    catalog: &Catalog,
) -> Result<Expr, DataFusionError> {
    use datafusion::logical_expr::LogicalPlan::*;

    let is_qualified = input_dfschema
        .fields()
        .iter()
        .all(|f| f.qualifier().is_some());

    let from: String = if is_qualified {
        // If the input DF schema is qualified, we can restrict the FROM-clause to the tables in the given schema
        let qualifiers: HashSet<String> = input_dfschema
            .fields()
            .iter()
            .map(|f| {
                let qualifier = f.qualifier().unwrap().to_string();
                let relname = catalog.resolve_alias(&qualifier);
                match relname {
                    Some(relname) => format!("{} as {}", relname, qualifier.to_lowercase()),
                    None => qualifier,
                }
            })
            .collect();
        qualifiers.into_iter().collect::<Vec<_>>().join(", ")
    } else {
        // If the input DF schema is not qualified, we cannot do better than making a FROM-clause with all tables in the catalog
        catalog.build_from_clause()
    };
    let sql = format!("SELECT * FROM {} WHERE {};", from, where_clause);

    let state = catalog.get_state();
    let plan = state.create_logical_plan(&sql).await?;

    // Do type coercion to ensure that the types of the operands are correct in case of comparison
    let coerced_plan = TypeCoercion::new().analyze(plan, state.config_options())?;
    let optimized_plan = UnwrapCastInComparison::new()
        .try_optimize(&coerced_plan, &state)?
        .unwrap_or(coerced_plan);

    match optimized_plan {
        Projection(p) => match p.input.as_ref() {
            Filter(f) => {
                return Ok(f.predicate.clone());
            }
            _ => todo!(),
        },
        _ => todo!(),
    }
}

/// Parse a SQL WHERE clause into a physical expression.
/// `input_dfschema` and `input_schema` are the arrow and datafusion schemas of the input relation
/// and must be compatible.
async fn where_clause_to_physical_expr(
    where_clause: &str,
    input_dfschema: &DFSchema,
    input_schema: &Schema,
    catalog: &Catalog,
) -> Result<Arc<dyn PhysicalExpr>, DataFusionError> {
    assert_eq!(
        input_dfschema.fields().len(),
        input_schema.fields().len(),
        "Mismatched schemas in where_clause_to_physical_expr. DFSchema: {}, Schema: {}",
        input_dfschema,
        input_schema
    );
    let expr = where_clause_to_logical_expr(where_clause, input_dfschema, catalog).await?;
    create_physical_expr(&expr, input_dfschema, input_schema, &ExecutionProps::new())
}

fn aggr_fn(name: &str) -> datafusion::physical_plan::aggregates::AggregateFunction {
    use datafusion::physical_plan::aggregates::AggregateFunction::*;

    match name.to_lowercase().as_ref() {
        "min" => Min,
        "max" => Max,
        "sum" => Sum,
        "avg" => Avg,
        "count" => Count,
        _ => panic!("Invalid aggregate function"),
    }
}

/// Split an aggregate expression into an aggregate function and an input column.
/// e.g: "min(a)" -> (Min, "a")
fn split_aggr_expr(
    expr: &str,
) -> (
    datafusion::physical_plan::aggregates::AggregateFunction,
    String,
) {
    let re = Regex::new(r"^\s*(\w+)\s*\(\s*([^)]+)\s*\)\s*$").unwrap();
    if let Some(captures) = re.captures(expr) {
        let aggr_fn = aggr_fn(&captures[1]);
        let input = captures[2].to_string();
        return (aggr_fn, input);
    }
    panic!("Invalid aggregate expression");
}

/// Convert aggregate expressions as strings to physical expressions ([AggregateExpr])
pub async fn parse_aggr_exprs(
    aggregate_exprs: &[String], // e.g. ["min(a)", "max(b)"]
    input_dfschema: &DFSchema,
    input_schema: &Schema,
    catalog: &Catalog,
) -> Result<(Vec<usize>, Vec<Arc<dyn AggregateExpr>>), DataFusionError> {
    use datafusion::physical_plan::aggregates::AggregateFunction::*;

    let mut indices: Vec<usize> = Vec::with_capacity(aggregate_exprs.len());

    // convert each aggregate as a string to a DF aggregate expression
    let aggr_exprs = aggregate_exprs
        .iter()
        .map(|expr| {
            if expr.to_lowercase() == "count(*)" || expr.to_lowercase() == "count_star()" {
                let cols = input_dfschema
                    .fields()
                    .iter()
                    .enumerate()
                    .map(|(i, f)| Arc::new(Column::new(f.name(), i)) as Arc<dyn PhysicalExpr>)
                    .collect::<Vec<_>>();
                create_aggregate_expr(&Count, false, &cols, &[], input_schema, "count(*)")
            } else {
                let (fun, input) = split_aggr_expr(expr);
                // convert "a" or "R.a" to column expr
                let input = input.split('.').collect::<Vec<&str>>();
                let (table, field): (Option<&str>, &str) = match input.len() {
                    1 => (None, input[0]),
                    2 => (Some(input[0]), input[1]),
                    _ => panic!("Invalid input"),
                };
                let col_id =
                    index_of_column_by_name(input_dfschema, table, field, catalog.aliases())?
                        .expect(&format!(
                            "Field {:?}.{} in aggregate expression not found",
                            table, field
                        ));
                let col = Column::new(field, col_id);
                indices.push(col_id);
                create_aggregate_expr(&fun, false, &[Arc::new(col)], &[], input_schema, expr)
            }
        })
        .collect::<Result<Vec<_>, _>>()?;

    Ok((indices, aggr_exprs))
}

#[cfg(test)]
mod tests {
    use datafusion::{
        physical_plan::display::DisplayableExecutionPlan,
        prelude::{SessionConfig, SessionContext},
    };
    use intermediate_plan::Plan;
    use std::path::Path;

    use super::*;

    async fn init_catalog(batch_size: usize, data_dir: &Path) -> Catalog {
        let ctx = SessionContext::new_with_config(
            SessionConfig::new()
                .with_batch_size(batch_size)
                .with_target_partitions(1),
        );

        let mut catalog = Catalog::new_with_context(ctx);
        catalog.add_parquets(data_dir, batch_size).await;

        catalog
    }

    #[tokio::test]
    async fn sequential_scan() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r"
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_alias() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r"
            },
            "aliases": {
                "r1": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_unqualified_filter() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r",
                "opt_filter": "a>=2"
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_qualified_filter() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r",
                "opt_filter": "r.a>=2"
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_filter_not_in_projection() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "b"
                    }
                ],
                "children": [],
                "relation": "r",
                "opt_filter": "a >= 2 and a IS NOT NULL"
            },
            "aliases": {
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[1])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_alias_and_unqualified_filter() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r",
                "opt_filter": "a >= 2"
            },
            "aliases": {
                "r1": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn sequential_scan_with_alias_and_qualified_filter() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "SEQUENTIALSCAN",
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    }
                ],
                "children": [],
                "relation": "r",
                "opt_filter": "r1.a >= 2"
            },
            "aliases": {
                "r1": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn filter_unqualified() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "FILTER",
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r1",
                        "field_name": "b"
                    }
                ],
                "execution_time": 2e-05,
                "actual_rows": 1,
                "children": [
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "r1",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r1",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "r"
                    }
                ],
                "condition": "(a <= b)"
            },
            "aliases": {
                "r1": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0, 1])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn filter_qualified() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "FILTER",
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r1",
                        "field_name": "b"
                    }
                ],
                "execution_time": 2e-05,
                "actual_rows": 1,
                "children": [
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "r1",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r1",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "r"
                    }
                ],
                "condition": "(r1.a <= r1.b)"
            },
            "aliases": {
                "r1": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let expected = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0, 1])?,
        )?;

        assert_eq!(schema.as_ref(), &expected);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn yannakakis_join() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "YANNAKAKIS",
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r",
                        "field_name": "b"
                    },
                    {
                        "table_name": "s",
                        "field_name": "a"
                    },
                    {
                        "table_name": "s",
                        "field_name": "b"
                    }
                ],
                "root": {
                    "name": "MULTISEMIJOIN",
                    "equijoin_keys": [
                        [[0,0],[1,1]]
                    ],
                    "guard": {
                        "name": "SEQUENTIALSCAN",
                        "relation": "r",
                        "output": [
                            {
                                "table_name": "r",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r",
                                "field_name": "b"
                            }
                        ],
                        "children": []
                    },
                    "children": [
                        {
                            "name": "GROUPBY",
                            "group_on": [0,1],
                            "child": {
                                "name": "MULTISEMIJOIN",
                                "equijoin_keys": [],
                                "guard": {
                                    "name": "SEQUENTIALSCAN",
                                    "relation": "s",
                                    "output": [
                                        {
                                            "table_name": "s",
                                            "field_name": "a"
                                        },
                                        {
                                            "table_name": "s",
                                            "field_name": "b"
                                        }
                                    ],
                                    "children": []
                                },
                                "children": []
                            }
                        }
                    ]
                }
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let r_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[0, 1])?,
        )?;
        let s_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("s"),
            &catalog.schemaof("s").project(&[0, 1])?,
        )?;

        let expected_schema = r_schema.join(&s_schema)?;
        assert_eq!(schema.as_ref(), &expected_schema);

        let plan = execution_plan
            .as_any()
            .downcast_ref::<Flatten>()
            .unwrap()
            .as_json()?;

        insta::with_settings!({
            description => format!("{:#?}", execution_plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(plan);
        });

        Ok(())
    }

    #[tokio::test]
    async fn hashjoin() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": 
            {
                "name": "HASHJOIN",
                "condition": [
                    [
                        {
                            "table_name": "r",
                            "field_name": "a"
                        },
                        {
                            "table_name": "s",
                            "field_name": "a"
                        }
                    ]
                ],
                "output": [
                    {
                        "table_name": "r",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r",
                        "field_name": "b"
                    },
                    {
                        "table_name": "s",
                        "field_name": "a"
                    },
                    {
                        "table_name": "s",
                        "field_name": "b"
                    }
                ],
                "children": [
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "r",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "r"
                    },
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "s",
                                "field_name": "a"
                            },
                            {
                                "table_name": "s",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "s"
                    }
                ]
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let r_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("r"),
            &catalog.schemaof("r").project(&[0, 1])?,
        )?;

        let s_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("s"),
            &catalog.schemaof("s").project(&[0, 1])?,
        )?;

        // DataFusion join output = build side + probe side
        // In our intermediate representation, the probe child (r) comes first
        // So we must swap the schemas here.
        assert_eq!(schema.as_ref(), &s_schema.join(&r_schema)?);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    async fn hashjoin_selfjoin_with_alias() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": {
                "name": "HASHJOIN",
                "condition": [
                    [
                        {
                            "table_name": "r1",
                            "field_name": "a"
                        },
                        {
                            "table_name": "r2",
                            "field_name": "a"
                        }
                    ]
                ],
                "output": [
                    {
                        "table_name": "r1",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r1",
                        "field_name": "b"
                    },
                    {
                        "table_name": "r2",
                        "field_name": "a"
                    },
                    {
                        "table_name": "r2",
                        "field_name": "b"
                    }
                ],
                "children": [
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "r1",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r1",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "r"
                    },
                    {
                        "name": "SEQUENTIALSCAN",
                        "output": [
                            {
                                "table_name": "r2",
                                "field_name": "a"
                            },
                            {
                                "table_name": "r2",
                                "field_name": "b"
                            }
                        ],
                        "children": [],
                        "relation": "r"
                    }
                ]
            },
            "aliases": {
                "r1": "r",
                "r2": "r"
            }
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (schema, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        let r1_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("r1"),
            &catalog.schemaof("r").project(&[0, 1])?,
        )?;

        let r2_schema = DFSchema::try_from_qualified_schema(
            TableReference::bare("r2"),
            &catalog.schemaof("s").project(&[0, 1])?,
        )?;

        // DataFusion join output = build side + probe side
        // In our intermediate representation, the probe child (r) comes first
        // So we must swap the schemas here.
        assert_eq!(schema.as_ref(), &r2_schema.join(&r1_schema)?);

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }

    #[tokio::test]
    /// aggregate on top of a join with a projection inbetween.
    async fn test_aggr_proj_join() -> Result<(), DataFusionError> {
        let mut catalog = init_catalog(1024, Path::new("testdata/parquet/")).await;

        let json = r#"
        {
            "root": {
                "name": "AGGREGATE",
                "output": [
                    {
                        "table_name": null,
                        "field_name": "min(r.a)"
                    },
                    {
                        "table_name": null,
                        "field_name": "min(s.b)"
                    }
                ],
                "children": [
                    {
                        "name": "PROJECTION",
                        "output": [
                            {
                                "table_name": "r",
                                "field_name": "a"
                            },
                            {
                                "table_name": "s",
                                "field_name": "b"
                            }
                        ],
                        "children": [
                            {
                                "name": "HASHJOIN",
                                "condition": [
                                    [
                                        {
                                            "table_name": "r",
                                            "field_name": "a"
                                        },
                                        {
                                            "table_name": "s",
                                            "field_name": "a"
                                        }
                                    ]
                                ],
                                "output": [
                                    {
                                        "table_name": "r",
                                        "field_name": "a"
                                    },
                                    {
                                        "table_name": "r",
                                        "field_name": "b"
                                    },
                                    {
                                        "table_name": "s",
                                        "field_name": "a"
                                    },
                                    {
                                        "table_name": "s",
                                        "field_name": "b"
                                    }
                                ],
                                "children": [
                                    {
                                        "name": "SEQUENTIALSCAN",
                                        "output": [
                                            {
                                                "table_name": "r",
                                                "field_name": "a"
                                            },
                                            {
                                                "table_name": "r",
                                                "field_name": "b"
                                            }
                                        ],
                                        "children": [],
                                        "relation": "r"
                                    },
                                    {
                                        "name": "SEQUENTIALSCAN",
                                        "output": [
                                            {
                                                "table_name": "s",
                                                "field_name": "a"
                                            },
                                            {
                                                "table_name": "s",
                                                "field_name": "b"
                                            }
                                        ],
                                        "children": [],
                                        "relation": "s"
                                    }
                                ]
                            }
                        ],
                        "on": [
                            {
                                "table_name": "r",
                                "field_name": "a"
                            },
                            {
                                "table_name": "s",
                                "field_name": "b"
                            }
                        ]
                    }
                ],
                "group_by": null,
                "aggregate": [
                    "min(r.a)",
                    "min(s.b)"
                ]
            },
            "aliases": {}
        }
        "#;

        let plan = serde_json::from_str::<Plan>(json).expect("Invalid JSON");
        catalog.update_aliases(&plan);
        let (_, execution_plan) = plan.root.to_execution_plan(&catalog, false).await?;

        insta::with_settings!({
            description => format!("{:#?}", plan),
            omit_expression => true
        }, {
            insta::assert_snapshot!(DisplayableExecutionPlan::new(execution_plan.as_ref())
            .indent(true)
            .to_string());
        });

        Ok(())
    }
}
