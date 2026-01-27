#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000;
typedef bitset<MAXN> bs;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<bs> D(n), F(n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            if (x) D[i].set(j);
        }
    }
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            if (x) F[i].set(j);
        }
    }
    
    // precompute flow rows and columns
    vector<bs> F_row = F;
    vector<bs> F_col(n);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            if (F[i][j])
                F_col[j].set(i);
    
    // facility total flow (out + in)
    vector<int> flow_sum(n);
    for (int i = 0; i < n; ++i)
        flow_sum[i] = F_row[i].count() + F_col[i].count();
    
    // location total distance (ones in row)
    vector<int> dist_sum(n);
    for (int i = 0; i < n; ++i)
        dist_sum[i] = D[i].count();
    
    // initial permutation: assign high-flow facilities to low-distance locations
    vector<int> fac_idx(n), loc_idx(n);
    iota(fac_idx.begin(), fac_idx.end(), 0);
    iota(loc_idx.begin(), loc_idx.end(), 0);
    sort(fac_idx.begin(), fac_idx.end(), [&](int i, int j) { return flow_sum[i] > flow_sum[j]; });
    sort(loc_idx.begin(), loc_idx.end(), [&](int i, int j) { return dist_sum[i] < dist_sum[j]; });
    
    vector<int> p(n); // p[facility] = location
    for (int k = 0; k < n; ++k)
        p[fac_idx[k]] = loc_idx[k];
    
    vector<int> q(n); // q[location] = facility
    for (int i = 0; i < n; ++i)
        q[p[i]] = i;
    
    // precompute in/out neighbourhoods of D
    vector<bs> out_neigh_D = D;
    vector<bs> in_neigh_D(n);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            if (D[i][j])
                in_neigh_D[j].set(i);
    
    // maintain for each location the set of facilities assigned to its D‑neighbours
    vector<bs> assigned_to_D_out(n), assigned_to_D_in(n);
    for (int a = 0; a < n; ++a) {
        bs &out = out_neigh_D[a];
        for (int y = out._Find_first(); y < n; y = out._Find_next(y))
            assigned_to_D_out[a].set(q[y]);
        bs &in = in_neigh_D[a];
        for (int y = in._Find_first(); y < n; y = in._Find_next(y))
            assigned_to_D_in[a].set(q[y]);
    }
    
    // local search (three passes)
    const int MAX_ITER = 3;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        bool improved = false;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int a = p[i], b = p[j];
                if (a == b) continue;
                
                int D_ba = D[b][a], D_ab = D[a][b];
                int F_ij = F[i][j], F_ji = F[j][i];
                int delta_dir = (D_ba - D_ab) * (F_ij - F_ji);
                
                int D_bb = D[b][b], D_aa = D[a][a];
                int F_ii = F[i][i], F_jj = F[j][j];
                int delta_diag = (D_bb - D_aa) * (F_ii - F_jj);
                
                bs &row_i = F_row[i], &col_i = F_col[i];
                bs &row_j = F_row[j], &col_j = F_col[j];
                
                int cnt_i_b   = (row_i & assigned_to_D_out[b]).count();
                int cnt_i_a   = (row_i & assigned_to_D_out[a]).count();
                int cnt_ri_b  = (col_i & assigned_to_D_in[b] ).count();
                int cnt_ri_a  = (col_i & assigned_to_D_in[a] ).count();
                int cnt_j_a   = (row_j & assigned_to_D_out[a]).count();
                int cnt_j_b   = (row_j & assigned_to_D_out[b]).count();
                int cnt_rj_a  = (col_j & assigned_to_D_in[a] ).count();
                int cnt_rj_b  = (col_j & assigned_to_D_in[b] ).count();
                
                // subtract contributions of i and j
                cnt_i_b  -= (row_i[i] && D_ba) + (row_i[j] && D_bb);
                cnt_i_a  -= (row_i[i] && D_aa) + (row_i[j] && D_ab);
                cnt_ri_b -= (col_i[i] && D_ab) + (col_i[j] && D_bb);
                cnt_ri_a -= (col_i[i] && D_aa) + (col_i[j] && D_ba);
                cnt_j_a  -= (row_j[i] && D_aa) + (row_j[j] && D_ab);
                cnt_j_b  -= (row_j[i] && D_ba) + (row_j[j] && D_bb);
                cnt_rj_a -= (col_j[i] && D_aa) + (col_j[j] && D_ba);
                cnt_rj_b -= (col_j[i] && D_ab) + (col_j[j] && D_bb);
                
                int delta = delta_dir + delta_diag
                          + (cnt_i_b - cnt_i_a) + (cnt_ri_b - cnt_ri_a)
                          + (cnt_j_a - cnt_j_b) + (cnt_rj_a - cnt_rj_b);
                
                if (delta < 0) {
                    // perform swap
                    p[i] = b; p[j] = a;
                    q[a] = j; q[b] = i;
                    
                    // update assigned_to_D_out
                    bs affected_out = in_neigh_D[a] | in_neigh_D[b];
                    for (int x = affected_out._Find_first(); x < n; x = affected_out._Find_next(x)) {
                        if (in_neigh_D[a][x]) {
                            assigned_to_D_out[x].reset(i);
                            assigned_to_D_out[x].set(j);
                        }
                        if (in_neigh_D[b][x]) {
                            assigned_to_D_out[x].reset(j);
                            assigned_to_D_out[x].set(i);
                        }
                    }
                    
                    // update assigned_to_D_in
                    bs affected_in = out_neigh_D[a] | out_neigh_D[b];
                    for (int x = affected_in._Find_first(); x < n; x = affected_in._Find_next(x)) {
                        if (out_neigh_D[a][x]) {
                            assigned_to_D_in[x].reset(i);
                            assigned_to_D_in[x].set(j);
                        }
                        if (out_neigh_D[b][x]) {
                            assigned_to_D_in[x].reset(j);
                            assigned_to_D_in[x].set(i);
                        }
                    }
                    
                    improved = true;
                }
            }
        }
        if (!improved) break;
    }
    
    // output permutation (1‑based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i] + 1;
    }
    cout << endl;
    
    return 0;
}