/**
 * Build the L5-compatible FilteredSchema from L3 retrieval results.
 */

/**
 * @param {Array}  l3Tables  - Dialect-filtered tables from L3
 * @param {Object} l3Result  - Full L3 response (for join_graph)
 * @returns {Object} FilteredSchema { tables, join_graph }
 */
export function buildFilteredSchema(l3Tables, l3Result) {
  const l3TableIds = new Set(l3Tables.map(t => t.table_id))

  const tables = l3Tables.map(t => {
    const cols = (t.visible_columns || t.columns || []).map(c => ({
      name: c.name,
      data_type: c.data_type || 'TEXT',
      nl_description: c.description || '',
      is_masked: c.visibility === 'MASKED',
      sql_rewrite: c.masking_expression || c.computed_expression || null,
    }))

    console.log(`[Schema Builder] Table ${t.table_id}: ${cols.length} columns`, cols.map(c => c.name))

    return {
      table_id: t.table_id,
      table_name: t.table_name || t.table_id,
      domain: (t.domain_tags || [])[0] || '',
      nl_description: t.description || '',
      relevance_score: t.relevance_score || 0,
      columns: cols,
      row_filters: t.row_filters || [],
      aggregation_only: t.aggregation_only || false,
    }
  })

  const joinGraph = (l3Result.join_graph?.edges || [])
    .filter(e =>
      l3TableIds.has(e.source_table || e.source) &&
      l3TableIds.has(e.target_table || e.target)
    )
    .map(e => ({
      from_table: e.source_table || e.source,
      from_column: e.source_column || '',
      to_table: e.target_table || e.target,
      to_column: e.target_column || '',
    }))

  console.log('[Schema Builder] Final schema:', {
    tableCount: tables.length,
    tableIds: tables.map(t => t.table_id),
    joinEdges: joinGraph.length,
  })

  return { tables, join_graph: joinGraph }
}
