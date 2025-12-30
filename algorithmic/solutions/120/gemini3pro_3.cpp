#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int adj[105][105];
int n = 100;

// Cache queries to avoid repeating
map<vector<int>, int> cache_q;

int query(int a, int b, int c) {
    if (a > b) swap(a, b);
    if (b > c) swap(b, c);
    if (a > b) swap(a, b);
    vector<int> v = {a, b, c};
    if (cache_q.count(v)) return cache_q[v];
    
    cout << "? " << a + 1 << " " << b + 1 << " " << c + 1 << endl;
    int res;
    cin >> res;
    return cache_q[v] = res;
}

int main() {
    // 1. Solve base graph for first K vertices
    int K = 5;
    while (true) {
        int edges_count = K * (K - 1) / 2;
        vector<pair<int, int>> edges;
        for (int i = 0; i < K; ++i) {
            for (int j = i + 1; j < K; ++j) {
                edges.push_back({i, j});
            }
        }

        // Collect all triplet queries
        vector<tuple<int, int, int, int>> constraints; // a, b, c, res
        for (int i = 0; i < K; ++i) {
            for (int j = i + 1; j < K; ++j) {
                for (int k = j + 1; k < K; ++k) {
                    constraints.emplace_back(i, j, k, query(i, j, k));
                }
            }
        }

        vector<vector<int>> solutions;
        // Brute force all edge configurations
        // Max edges = 10 (for K=5), 2^10 = 1024
        int total_configs = 1 << edges_count;
        for (int mask = 0; mask < total_configs; ++mask) {
            // Check consistency
            bool ok = true;
            // Build temporary adj
            int temp_adj[10][10] = {0};
            for (int e = 0; e < edges_count; ++e) {
                if ((mask >> e) & 1) {
                    temp_adj[edges[e].first][edges[e].second] = 1;
                    temp_adj[edges[e].second][edges[e].first] = 1;
                }
            }
            
            for (auto& t : constraints) {
                int a, b, c, res;
                tie(a, b, c, res) = t;
                if (temp_adj[a][b] + temp_adj[b][c] + temp_adj[a][c] != res) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                vector<int> sol(edges_count);
                for (int e = 0; e < edges_count; ++e) sol[e] = (mask >> e) & 1;
                solutions.push_back(sol);
            }
        }

        if (solutions.size() == 1) {
            // Unique solution found
            for (int e = 0; e < edges_count; ++e) {
                int u = edges[e].first;
                int v = edges[e].second;
                adj[u][v] = adj[v][u] = solutions[0][e];
            }
            break;
        }
        
        // If not unique, increase K
        K++;
        if (K > 10) { // Safety break, should not happen
            break; 
        }
    }

    // 2. Iteratively add vertices
    int current_size = K;
    while (current_size < n) {
        if (current_size == n - 1) {
            // Handle last single vertex
            int v = current_size;
            // Pair up existing vertices (0,1), (2,3)...
            // We need to determine edges from v to 0..current_size-1
            // Use M=1 strategy: pair elements in S
            vector<int> S;
            for(int i=0; i<current_size; ++i) S.push_back(i);
            
            // We need to resolve edge(v, u) for all u in S.
            // Pair them up
            vector<int> x(current_size, -1); // -1 unknown
            vector<pair<int, int>> pairs;
            vector<int> ambiguous_indices;
            
            for (int i = 0; i + 1 < current_size; i += 2) {
                int u1 = S[i];
                int u2 = S[i+1];
                int q = query(v, u1, u2); // x_u1 + x_u2 + e_u1u2
                int sum = q - adj[u1][u2];
                // sum can be 0, 1, 2
                if (sum == 0) {
                    adj[v][u1] = adj[u1][v] = 0;
                    adj[v][u2] = adj[u2][v] = 0;
                } else if (sum == 2) {
                    adj[v][u1] = adj[u1][v] = 1;
                    adj[v][u2] = adj[u2][v] = 1;
                } else {
                    // Ambiguous
                    // Record relative constraint?
                    // Actually, simpler: query with a determined node
                    // We need to find ONE determined node first.
                    ambiguous_indices.push_back(i); 
                }
            }
            
            // Check if last element remains
            if (current_size % 2 != 0) {
                // Handle separately or pair with 0
                int u = S[current_size - 1];
                int u0 = S[0]; // Guaranteed to exist
                // Just do standard query with u0 (which might be ambiguous? No, we resolve all eventually)
                // Add to ambiguous list for uniform handling, treating (u, u0) as pair
                // But we need to be careful about dependency.
                // Let's postpone.
            }
            
            // Find a determined node
            int det_node = -1;
            for (int i = 0; i < current_size; ++i) {
                // If this node was part of a 0/2 sum pair, it is determined
                // Wait, I updated adj directly.
                // How to check? Init adj with -1?
                // adj is global, init to 0. 
                // Better track solved status.
            }
            // Actually, we can just check if we updated adj.
            // But we didn't mark "updated".
            // Let's use a temporary array for edges to v
            vector<int> edge_vals(current_size, -1);
             for (int i = 0; i + 1 < current_size; i += 2) {
                int u1 = S[i];
                int u2 = S[i+1];
                int q = query(v, u1, u2);
                int sum = q - adj[u1][u2];
                if (sum == 0) {
                    edge_vals[u1] = 0;
                    edge_vals[u2] = 0;
                    det_node = u1;
                } else if (sum == 2) {
                    edge_vals[u1] = 1;
                    edge_vals[u2] = 1;
                    det_node = u1;
                } else {
                    // sum == 1, x_u1 + x_u2 = 1
                }
            }

            // If we have an odd one out
            if (current_size % 2 != 0) {
                 // We will handle it in resolution phase
            }

            // If no determined node found (all pairs ambiguous), pick one pair and resolve
            if (det_node == -1) {
                // All pairs sum to 1.
                // Pick pair 0 (u1, u2).
                // Try x_u1 = 0 => x_u2 = 1.
                // Try x_u1 = 1 => x_u2 = 0.
                // We need to distinguish.
                // Pick pair 1 (u3, u4).
                // Query (v, u1, u3).
                // If we assume x_u1, we find x_u3.
                // This links pairs.
                // Link all pairs to pair 0.
                // Then we have 2 global candidates.
                // Check consistency with one query?
                // Or just: if no det node, we query ONE triplet (v, u1, u3) to link.
                // Still we have global flip ambiguity.
                // We need to break it.
                // Can we use a triplet of u's? No.
                // Query (v, u1, u2) was 1.
                // Query (v, u3, u4) was 1.
                // Query (v, u1, u3).
                // This gives x1 + x3 relation.
                // This links.
                // Global flip remains.
                // To fix global flip: pick u1, u2. x1+x2=1.
                // We need x1.
                // Query (u1, u2, v)? No we did that.
                // Query (u1, u2, u3)? No v involved.
                // Maybe just query (v, u1, u2) again? No.
                // We need something else.
                // Ah, (v, u1, u3) gives sum x1+x3.
                // If we assume x1=0 => x3 known.
                // We can construct full candidate vector X.
                // Then check consistency with Q(v, u1, u2)? No that matches by definition.
                // Wait, is there any other query?
                // Actually, just pick any 3 solved nodes u_a, u_b, u_c.
                // We can find x_a, x_b, x_c using 3 queries (v, a, b), (v, b, c), (v, a, c).
                // This gives x_a+x_b, x_b+x_c, x_a+x_c.
                // Solvable!
                // So if no determined node, pick first 3 nodes (0, 1, 2) and re-solve using triangle method.
                // (0,1) already queried. (2,3) already queried.
                // Just query (v, 1, 2).
                // We have (v, 0, 1) -> x0+x1.
                // We have (v, 2, 3) -> x2+x3.
                // Query (v, 1, 2) -> x1+x2.
                // Still detached components {0,1} and {2,3}.
                // We need triangle on {0, 1, 2}.
                // We have x0+x1. Query (v, 1, 2) -> x1+x2. Query (v, 0, 2) -> x0+x2.
                // Solve for x0, x1, x2.
                // Then we have determined nodes!
                
                // Do triangle on 0, 1, 2
                int u0=0, u1=1, u2=2;
                int S01 = query(v, u0, u1) - adj[u0][u1];
                int S12 = query(v, u1, u2) - adj[u1][u2];
                int S02 = query(v, u0, u2) - adj[u0][u2];
                
                edge_vals[u0] = (S01 + S02 - S12) / 2;
                edge_vals[u1] = (S01 + S12 - S02) / 2;
                edge_vals[u2] = (S02 + S12 - S01) / 2;
                det_node = u0;
            }

            // Now resolve all others using det_node
            for (int i = 0; i < current_size; ++i) {
                if (edge_vals[i] != -1) continue; // Already determined
                // If this node i was part of a pair (i, j)
                // We might know x_i + x_j.
                // If j is determined, i is determined.
                // If neither determined, query (v, i, det_node).
                
                // Simpler: Just iterate all unknown i.
                // Query (v, i, det_node).
                int q = query(v, i, det_node);
                edge_vals[i] = q - adj[i][det_node] - edge_vals[det_node];
            }
            
            for(int i=0; i<current_size; ++i) {
                adj[v][i] = adj[i][v] = edge_vals[i];
            }
            
            current_size++;
        } 
        else {
            // Add two vertices v1, v2
            int v1 = current_size;
            int v2 = current_size + 1;
            
            // Collect info
            vector<int> Q(current_size);
            int det_z = -1; // -1 unknown, 0 or 1
            
            for (int u = 0; u < current_size; ++u) {
                Q[u] = query(u, v1, v2);
                if (Q[u] == 0) det_z = 0;
                else if (Q[u] == 3) det_z = 1;
            }
            
            int z = -1; // e(v1, v2)
            if (det_z != -1) {
                z = det_z;
            } else {
                // Try to deduce z
                // For each u, if z=0: vals are deduced.
                // If z=1: vals are deduced.
                // Check consistency?
                // Actually, if we assume z, we get classifications of u.
                // We just need one query to distinguish.
                // Pick u0.
                // If z=0 => x0, y0 determined (e.g. 1, 1 if Q=2; 0,0 if Q=0 - covered above).
                // Since det_z == -1, all Q are 1 or 2.
                // If Q=1 => x+y+z=1. z=0 -> x!=y. z=1 -> x=y=0.
                // If Q=2 => x+y+z=2. z=0 -> x=y=1. z=1 -> x!=y.
                
                // Pick two nodes u_a, u_b.
                // Query Q(v1, u_a, u_b).
                // Predict result under z=0 and z=1.
                // If different, we are good.
                
                // We need to form candidate vectors for x (edges to v1) and y (edges to v2).
                // Let X0, Y0 be vectors if z=0.
                // Let X1, Y1 be vectors if z=1.
                // For u where Q=1:
                //   z=0 -> x!=y. Ambiguous. We can't set X0[u] yet.
                //   z=1 -> x=y=0. Fixed. X1[u]=0, Y1[u]=0.
                // For u where Q=2:
                //   z=0 -> x=y=1. Fixed. X0[u]=1, Y0[u]=1.
                //   z=1 -> x!=y. Ambiguous.
                
                // We have a mix of fixed and ambiguous.
                // Note that ambiguity is always x = 1-y.
                // We can't determine z solely by u-wise consistency.
                
                // Let's create X0, Y0 with "unknowns" represented by ID.
                // But simpler:
                // Just pick u_a (type 1: Q=1) and u_b (type 2: Q=2).
                // If we have both types:
                //   Assume z=0:
                //     u_a is amb (x_a + y_a = 1).
                //     u_b is fixed (x_b=1, y_b=1).
                //   Assume z=1:
                //     u_a is fixed (x_a=0, y_a=0).
                //     u_b is amb (x_b + y_b = 1).
                //   Query Q(v1, u_a, u_b) -> Sum = x_a + x_b + e_ab.
                //   Value V = Sum - e_ab = x_a + x_b.
                //   Under z=0: x_a + 1 = V => x_a = V - 1.
                //   Under z=1: 0 + x_b = V => x_b = V.
                //   Now check Q(v2, u_a, u_b) -> V2 = y_a + y_b.
                //   Under z=0: y_a + 1 = V2.
                //   Since x_a + y_a = 1, (V-1) + (V2-1) = 1 => V+V2 = 3.
                //   Under z=1: 0 + y_b = V2.
                //   Since x_b + y_b = 1, V + V2 = 1.
                //   So check V + V2. If 3 => z=0. If 1 => z=1.
                
                // Need to find u_a (Q=1) and u_b (Q=2).
                int idx1 = -1, idx2 = -1;
                for (int u = 0; u < current_size; ++u) {
                    if (Q[u] == 1) idx1 = u;
                    if (Q[u] == 2) idx2 = u;
                }
                
                if (idx1 != -1 && idx2 != -1) {
                    int qa = query(v1, idx1, idx2);
                    int qb = query(v2, idx1, idx2);
                    int e = adj[idx1][idx2];
                    int V1 = qa - e;
                    int V2 = qb - e;
                    if (V1 + V2 == 3) z = 0;
                    else z = 1;
                } 
                else if (idx1 != -1) {
                    // All are type 1 (Q=1).
                    // z=0 => All amb. z=1 => All fixed (0,0).
                    // Pick u_a, u_b.
                    // Under z=1: x_a=0, x_b=0 => x_a+x_b=0.
                    // Under z=0: x_a+y_a=1, x_b+y_b=1.
                    // Query V1 = x_a + x_b.
                    // Query V2 = y_a + y_b.
                    // Sum V1+V2 = (x_a+y_a) + (x_b+y_b) = 2.
                    // Under z=1: Sum = 0+0 = 0.
                    // So check V1+V2. If 2 => z=0. If 0 => z=1.
                    if (current_size >= 2) {
                        int qa = query(v1, 0, 1);
                        int qb = query(v2, 0, 1);
                        int e = adj[0][1];
                        if (qa - e + qb - e == 2) z = 0;
                        else z = 1;
                    } else {
                        // size < 2, not possible since K=5 start
                    }
                } 
                else {
                    // All are type 2 (Q=2).
                    // z=0 => All fixed (1,1).
                    // z=1 => All amb.
                    // Similar check.
                    // Under z=0: x_a=1, x_b=1 => sum=2.
                    // Under z=1: sum=2 (x+y=1 logic).
                    // Wait.
                    // z=0: x=1, y=1 => x+y=2. Sum pair = 2+2=4.
                    // z=1: x+y=1 => Sum pair = 1+1=2.
                    // So V1+V2 = 4 vs 2.
                    int qa = query(v1, 0, 1);
                    int qb = query(v2, 0, 1);
                    int e = adj[0][1];
                    if (qa - e + qb - e == 4) z = 0;
                    else z = 1;
                }
            }
            
            adj[v1][v2] = adj[v2][v1] = z;
            
            // Now z is known. Resolve edges.
            // Identify fixed and ambiguous
            vector<int> fixed_x(current_size, -1);
            vector<int> fixed_y(current_size, -1);
            vector<int> amb_list;
            
            int resolved_node = -1;
            
            for (int u = 0; u < current_size; ++u) {
                int q = Q[u];
                // x + y = q - z
                int s = q - z;
                if (s == 0) {
                    fixed_x[u] = 0; fixed_y[u] = 0;
                    resolved_node = u;
                } else if (s == 2) {
                    fixed_x[u] = 1; fixed_y[u] = 1;
                    resolved_node = u;
                } else {
                    amb_list.push_back(u);
                }
            }
            
            // If no resolved node, create one
            if (resolved_node == -1 && !amb_list.empty()) {
                // Pick first ambiguous, resolve it with a neighbor
                // We have no neighbor?
                // Use triangle on 0, 1, v1
                // We need to find x0, x1.
                // We know x0+y0=1, x1+y1=1.
                // Query (v1, 0, 1) -> x0+x1.
                // This links 0 and 1.
                // Still global ambiguity.
                // But we also have y0, y1.
                // Q(v2, 0, 1) -> y0+y1.
                // This is consistent and gives no new info.
                
                // We need a base.
                // Use the fact that we can do triangle on 0, 1, 2?
                // Just pick 0, 1, 2. Solve for x0, x1, x2 (edges to v1) using 3 queries on v1.
                // (v1, 0, 1), (v1, 1, 2), (v1, 0, 2).
                // x0+x1 = Q(v1, 0, 1) - e01.
                // x1+x2 = Q(v1, 1, 2) - e12.
                // x0+x2 = Q(v1, 0, 2) - e02.
                // Solve system.
                int u0 = amb_list[0];
                int u1 = amb_list[1];
                int u2 = amb_list[2]; // Assume at least 3 amb nodes if no resolved. K>=5.
                
                int A = query(v1, u0, u1) - adj[u0][u1];
                int B = query(v1, u1, u2) - adj[u1][u2];
                int C = query(v1, u0, u2) - adj[u0][u2];
                
                fixed_x[u0] = (A + C - B) / 2;
                fixed_x[u1] = (A + B - C) / 2;
                fixed_x[u2] = (C + B - A) / 2;
                
                // y is determined by x + y = 1
                fixed_y[u0] = 1 - fixed_x[u0];
                fixed_y[u1] = 1 - fixed_x[u1];
                fixed_y[u2] = 1 - fixed_x[u2];
                
                resolved_node = u0; // Now we have a base
            }
            
            // Resolve remaining ambiguous
            for (int u : amb_list) {
                if (fixed_x[u] != -1) continue;
                // Query against resolved_node
                // Q(v1, u, res) -> x_u + x_res
                int q = query(v1, u, resolved_node);
                int val = q - adj[u][resolved_node];
                fixed_x[u] = val - fixed_x[resolved_node];
                fixed_y[u] = 1 - fixed_x[u];
            }
            
            for (int u = 0; u < current_size; ++u) {
                adj[v1][u] = adj[u][v1] = fixed_x[u];
                adj[v2][u] = adj[u][v2] = fixed_y[u];
            }
            
            current_size += 2;
        }
    }
    
    cout << "!" << endl;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (i == j) cout << 0;
            else cout << adj[i][j];
        }
        cout << endl;
    }
    
    return 0;
}