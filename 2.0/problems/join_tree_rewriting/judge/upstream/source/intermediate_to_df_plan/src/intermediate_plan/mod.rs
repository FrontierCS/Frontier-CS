use std::collections::HashMap;

use serde::{Deserialize, Serialize};

mod yannakakis;
pub use yannakakis::{GroupByNode, MultiSemiJoinNode, YannakakisNode};

#[derive(Serialize, Deserialize, Debug)]
pub struct Plan {
    pub execution_time: Option<f64>,
    pub root: Node,
    pub aliases: HashMap<String, String>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "name", rename_all = "UPPERCASE")]
pub enum Node {
    Aggregate(AggregateNode),
    Projection(ProjectionNode),
    Filter(FilterNode),
    HashJoin(HashJoinNode),
    MergeJoin(MergeJoinNode),
    SequentialScan(SequentialScanNode),
    Yannakakis(Box<yannakakis::YannakakisNode>),
}

impl Node {
    pub fn children(&self) -> Box<dyn Iterator<Item = &Node> + '_> {
        match self {
            Node::Aggregate(n) => Box::new(n.base.children.iter()),
            Node::Projection(n) => Box::new(n.base.children.iter()),
            Node::Filter(n) => Box::new(n.base.children.iter()),
            Node::HashJoin(n) => Box::new(n.base.children.iter()),
            Node::MergeJoin(n) => Box::new(n.base.children.iter()),
            Node::SequentialScan(n) => Box::new(n.base.children.iter()),
            Node::Yannakakis(n) => n.children(),
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct BaseNode {
    pub execution_time: Option<f64>,
    pub actual_rows: Option<usize>,
    pub estimated_cardinality: Option<usize>,
    pub children: Vec<Node>,
    // pub output: Vec<Field>, // output fields are only specified for SeqScan & Projection
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AggregateNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub group_by: Option<Vec<Field>>,
    pub aggregate: Vec<String>, // e.g: vec!["min(mc.note)", "min(t.title)", "min(t.production_year)"]
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ProjectionNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub on: Vec<Field>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct FilterNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub condition: String,
}

pub type JoinOn = Vec<(Field, Field)>;

#[derive(Serialize, Deserialize, Debug)]
pub struct HashJoinNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub condition: JoinOn,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct MergeJoinNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub condition: JoinOn,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct SequentialScanNode {
    #[serde(flatten)]
    pub base: BaseNode,
    pub relation: String,
    pub projection: Vec<Field>,
    pub opt_filter: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Eq, Hash, PartialEq, Clone)]
pub struct Field {
    pub table_name: Option<String>, // None if not qualified
    pub field_name: String,
}

impl Field {
    #[allow(dead_code)]
    pub fn is_qualified(&self) -> bool {
        self.table_name.is_some()
    }

    /// Returns a new Field with the field name in lowercase.
    pub fn to_lowercase(&self) -> Field {
        Field {
            table_name: self.table_name.clone(),
            field_name: self.field_name.to_lowercase(),
        }
    }

    /// Returns a new Field with the table name and field name in lowercase.
    pub fn lowercase_all(&self) -> Field {
        Field {
            table_name: self.table_name.as_ref().map(|t| t.to_lowercase()),
            field_name: self.field_name.to_lowercase(),
        }
    }
}

// impl Field {
//     pub fn from(df_field: &DFField, dtype: &DataType, nullable: bool) -> Self {
//         let table_name = df_field.
//     }
// }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deserialize_plan() {
        let plan = r#"
        {
            "execution_time": 0.21533,
            "root": {
                "name": "AGGREGATE",
                "output": [
                    {
                        "table_name": null,
                        "field_name": "min(mc.note)"
                    },
                    {
                        "table_name": null,
                        "field_name": "min(t.title)"
                    },
                    {
                        "table_name": null,
                        "field_name": "min(t.production_year)"
                    }
                ],
                "execution_time": 1.3e-05,
                "actual_rows": 1,
                "children": [
                    {
                        "name": "PROJECTION",
                        "output": [
                            {
                                "table_name": "movie_companies",
                                "field_name": "note"
                            },
                            {
                                "table_name": "title",
                                "field_name": "title"
                            },
                            {
                                "table_name": "title",
                                "field_name": "production_year"
                            }
                        ],
                        "execution_time": 1e-06,
                        "actual_rows": 142,
                        "children": [
                            {
                                "name": "HASHJOIN",
                                "output": [
                                    {
                                        "table_name": "title",
                                        "field_name": "id"
                                    },
                                    {
                                        "table_name": "title",
                                        "field_name": "title"
                                    },
                                    {
                                        "table_name": "title",
                                        "field_name": "production_year"
                                    },
                                    {
                                        "table_name": "movie_companies",
                                        "field_name": "note"
                                    },
                                    {
                                        "table_name": "movie_companies",
                                        "field_name": "company_type_id"
                                    },
                                    {
                                        "table_name": "movie_companies",
                                        "field_name": "movie_id"
                                    },
                                    {
                                        "table_name": "movie_info_idx",
                                        "field_name": "movie_id"
                                    },
                                    {
                                        "table_name": "movie_info_idx",
                                        "field_name": "info_type_id"
                                    },
                                    {
                                        "table_name": "info_type",
                                        "field_name": "id"
                                    },
                                    {
                                        "table_name": "company_type",
                                        "field_name": "id"
                                    }
                                ],
                                "execution_time": 0.009966,
                                "actual_rows": 142,
                                "children": [
                                    {
                                        "name": "SEQUENTIALSCAN",
                                        "output": [
                                            {
                                                "table_name": "title",
                                                "field_name": "id"
                                            },
                                            {
                                                "table_name": "title",
                                                "field_name": "title"
                                            },
                                            {
                                                "table_name": "title",
                                                "field_name": "production_year"
                                            }
                                        ],
                                        "execution_time": 0.08041,
                                        "actual_rows": 2525744,
                                        "children": [],
                                        "relation": "title",
                                        "opt_filter": "id>=2 AND id<=2525745 AND id IS NOT NULL"
                                    },
                                    {
                                        "name": "HASHJOIN",
                                        "output": [
                                            {
                                                "table_name": "movie_companies",
                                                "field_name": "note"
                                            },
                                            {
                                                "table_name": "movie_companies",
                                                "field_name": "company_type_id"
                                            },
                                            {
                                                "table_name": "movie_companies",
                                                "field_name": "movie_id"
                                            },
                                            {
                                                "table_name": "movie_info_idx",
                                                "field_name": "movie_id"
                                            },
                                            {
                                                "table_name": "movie_info_idx",
                                                "field_name": "info_type_id"
                                            },
                                            {
                                                "table_name": "info_type",
                                                "field_name": "id"
                                            },
                                            {
                                                "table_name": "company_type",
                                                "field_name": "id"
                                            }
                                        ],
                                        "execution_time": 1.8e-05,
                                        "actual_rows": 142,
                                        "children": [
                                            {
                                                "name": "HASHJOIN",
                                                "output": [
                                                    {
                                                        "table_name": "movie_companies",
                                                        "field_name": "note"
                                                    },
                                                    {
                                                        "table_name": "movie_companies",
                                                        "field_name": "company_type_id"
                                                    },
                                                    {
                                                        "table_name": "movie_companies",
                                                        "field_name": "movie_id"
                                                    },
                                                    {
                                                        "table_name": "movie_info_idx",
                                                        "field_name": "movie_id"
                                                    },
                                                    {
                                                        "table_name": "movie_info_idx",
                                                        "field_name": "info_type_id"
                                                    },
                                                    {
                                                        "table_name": "info_type",
                                                        "field_name": "id"
                                                    }
                                                ],
                                                "execution_time": 0.000545,
                                                "actual_rows": 147,
                                                "children": [
                                                    {
                                                        "name": "FILTER",
                                                        "output": [
                                                            {
                                                                "table_name": "movie_companies",
                                                                "field_name": "note"
                                                            },
                                                            {
                                                                "table_name": "movie_companies",
                                                                "field_name": "company_type_id"
                                                            },
                                                            {
                                                                "table_name": "movie_companies",
                                                                "field_name": "movie_id"
                                                            }
                                                        ],
                                                        "execution_time": 0.07128,
                                                        "actual_rows": 28889,
                                                        "children": [
                                                            {
                                                                "name": "SEQUENTIALSCAN",
                                                                "output": [
                                                                    {
                                                                        "table_name": "movie_companies",
                                                                        "field_name": "note"
                                                                    },
                                                                    {
                                                                        "table_name": "movie_companies",
                                                                        "field_name": "company_type_id"
                                                                    },
                                                                    {
                                                                        "table_name": "movie_companies",
                                                                        "field_name": "movie_id"
                                                                    }
                                                                ],
                                                                "execution_time": 0.045442,
                                                                "actual_rows": 2609129,
                                                                "children": [],
                                                                "relation": "movie_companies",
                                                                "opt_filter": null
                                                            }
                                                        ],
                                                        "condition": "((NOT movie_companies.note LIKE '%(as Metro-Goldwyn-Mayer Pictures)%') AND (movie_companies.note LIKE '%(co-production)%' OR movie_companies.note LIKE '%(presents)%'))"
                                                    },
                                                    {
                                                        "name": "HASHJOIN",
                                                        "output": [
                                                            {
                                                                "table_name": "movie_info_idx",
                                                                "field_name": "movie_id"
                                                            },
                                                            {
                                                                "table_name": "movie_info_idx",
                                                                "field_name": "info_type_id"
                                                            },
                                                            {
                                                                "table_name": "info_type",
                                                                "field_name": "id"
                                                            }
                                                        ],
                                                        "execution_time": 0.002698,
                                                        "actual_rows": 250,
                                                        "children": [
                                                            {
                                                                "name": "SEQUENTIALSCAN",
                                                                "output": [
                                                                    {
                                                                        "table_name": "movie_info_idx",
                                                                        "field_name": "movie_id"
                                                                    },
                                                                    {
                                                                        "table_name": "movie_info_idx",
                                                                        "field_name": "info_type_id"
                                                                    }
                                                                ],
                                                                "execution_time": 0.002716,
                                                                "actual_rows": 1380011,
                                                                "children": [],
                                                                "relation": "movie_info_idx",
                                                                "opt_filter": "movie_id<=2525745 AND movie_id IS NOT NULL"
                                                            },
                                                            {
                                                                "name": "FILTER",
                                                                "output": [
                                                                    {
                                                                        "table_name": "info_type",
                                                                        "field_name": "id"
                                                                    }
                                                                ],
                                                                "execution_time": 2e-06,
                                                                "actual_rows": 1,
                                                                "children": [
                                                                    {
                                                                        "name": "SEQUENTIALSCAN",
                                                                        "output": [
                                                                            {
                                                                                "table_name": "info_type",
                                                                                "field_name": "id"
                                                                            }
                                                                        ],
                                                                        "execution_time": 6e-06,
                                                                        "actual_rows": 1,
                                                                        "children": [],
                                                                        "relation": "info_type",
                                                                        "opt_filter": "info='top 250 rank' AND info IS NOT NULL"
                                                                    }
                                                                ],
                                                                "condition": "(info_type.id >= 99)"
                                                            }
                                                        ],
                                                        "condition": [
                                                            [
                                                                {
                                                                    "table_name": "movie_info_idx",
                                                                    "field_name": "info_type_id"
                                                                },
                                                                {
                                                                    "table_name": "info_type",
                                                                    "field_name": "id"
                                                                }
                                                            ]
                                                        ]
                                                    }
                                                ],
                                                "condition": [
                                                    [
                                                        {
                                                            "table_name": "movie_companies",
                                                            "field_name": "movie_id"
                                                        },
                                                        {
                                                            "table_name": "movie_info_idx",
                                                            "field_name": "movie_id"
                                                        }
                                                    ]
                                                ]
                                            },
                                            {
                                                "name": "FILTER",
                                                "output": [
                                                    {
                                                        "table_name": "company_type",
                                                        "field_name": "id"
                                                    }
                                                ],
                                                "execution_time": 7e-06,
                                                "actual_rows": 1,
                                                "children": [
                                                    {
                                                        "name": "SEQUENTIALSCAN",
                                                        "output": [
                                                            {
                                                                "table_name": "company_type",
                                                                "field_name": "id"
                                                            }
                                                        ],
                                                        "execution_time": 1.2e-05,
                                                        "actual_rows": 1,
                                                        "children": [],
                                                        "relation": "company_type",
                                                        "opt_filter": "kind='production companies' AND kind IS NOT NULL"
                                                    }
                                                ],
                                                "condition": "(company_type.id <= 2)"
                                            }
                                        ],
                                        "condition": [
                                            [
                                                {
                                                    "table_name": "movie_companies",
                                                    "field_name": "company_type_id"
                                                },
                                                {
                                                    "table_name": "company_type",
                                                    "field_name": "id"
                                                }
                                            ]
                                        ]
                                    }
                                ],
                                "condition": [
                                    [
                                        {
                                            "table_name": "title",
                                            "field_name": "id"
                                        },
                                        {
                                            "table_name": "movie_info_idx",
                                            "field_name": "movie_id"
                                        }
                                    ]
                                ]
                            }
                        ],
                        "on": [
                            {
                                "table_name": "movie_companies",
                                "field_name": "note"
                            },
                            {
                                "table_name": "title",
                                "field_name": "title"
                            },
                            {
                                "table_name": "title",
                                "field_name": "production_year"
                            }
                        ]
                    }
                ],
                "group_by": null,
                "aggregate": [
                    "min(movie_companies.note)",
                    "min(title.title)",
                    "min(title.production_year)"
                ]
            },
            "aliases": {
                "ct": "company_type",
                "it": "info_type",
                "mc": "movie_companies",
                "mi_idx": "movie_info_idx",
                "t": "title"
            }
        }
        "#;

        let plan: Plan = serde_json::from_str(plan).unwrap();

        println!("{:#?}", plan)
    }
}
