#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cctype>
#include <sstream>
#include <cstring>

using namespace std;

typedef long long ll;

const ll M = 20000000;   // mass limit in mg
const ll L = 25000000;   // volume limit in µl

struct Group {
    ll mass, vol, value;
    int type;
};

int main() {
    // Read entire input
    string s;
    char ch;
    while (cin.get(ch)) s += ch;

    // Parse JSON
    vector<string> names;
    vector<ll> q, v, m, l;
    int pos = 0;
    auto skip_ws = [&]() {
        while (pos < (int)s.size() && isspace(s[pos])) pos++;
    };
    skip_ws();
    if (s[pos] != '{') return 1;
    pos++;
    for (int i = 0; i < 12; ++i) {
        skip_ws();
        if (s[pos] != '"') return 1;
        pos++;
        string key;
        while (pos < (int)s.size() && s[pos] != '"') key += s[pos++];
        if (s[pos] != '"') return 1;
        pos++;
        skip_ws();
        if (s[pos] != ':') return 1;
        pos++;
        skip_ws();
        if (s[pos] != '[') return 1;
        pos++;
        vector<ll> nums;
        for (int j = 0; j < 4; ++j) {
            skip_ws();
            ll num = 0;
            bool neg = false;
            if (s[pos] == '-') { neg = true; pos++; }
            while (pos < (int)s.size() && isdigit(s[pos])) {
                num = num * 10 + (s[pos] - '0');
                pos++;
            }
            if (neg) num = -num;
            nums.push_back(num);
            skip_ws();
            if (j < 3) {
                if (s[pos] != ',') return 1;
                pos++;
            }
        }
        skip_ws();
        if (s[pos] != ']') return 1;
        pos++;
        skip_ws();
        if (i < 11) {
            if (s[pos] != ',') return 1;
            pos++;
        }
        names.push_back(key);
        q.push_back(nums[0]);
        v.push_back(nums[1]);
        m.push_back(nums[2]);
        l.push_back(nums[3]);
    }
    skip_ws();
    if (s[pos] != '}') return 1;

    int n = 12;

    // Precompute mask values
    int total_masks = 1 << n;
    vector<ll> mass_mask(total_masks, 0), vol_mask(total_masks, 0), value_mask(total_masks, 0);
    for (int mask = 0; mask < total_masks; ++mask) {
        ll mass = 0, vol = 0, val = 0;
        for (int i = 0; i < n; ++i) {
            if (mask & (1 << i)) {
                mass += q[i] * m[i];
                vol += q[i] * l[i];
                val += q[i] * v[i];
            }
        }
        mass_mask[mask] = mass;
        vol_mask[mask] = vol;
        value_mask[mask] = val;
    }

    // Best solution found
    ll best_value = -1;
    vector<ll> best_counts(n, 0);

    // 1. All variables at bounds (0 or q[i])
    for (int mask = 0; mask < total_masks; ++mask) {
        if (mass_mask[mask] <= M && vol_mask[mask] <= L) {
            if (value_mask[mask] > best_value) {
                best_value = value_mask[mask];
                for (int i = 0; i < n; ++i)
                    best_counts[i] = (mask & (1 << i)) ? q[i] : 0;
            }
        }
    }

    // 2. One free variable
    for (int mask = 0; mask < total_masks; ++mask) {
        for (int i = 0; i < n; ++i) {
            int fixed_mask = mask & ~(1 << i);
            ll mass_fixed = mass_mask[fixed_mask];
            ll vol_fixed = vol_mask[fixed_mask];
            ll value_fixed = value_mask[fixed_mask];
            ll rm = M - mass_fixed;
            ll rv = L - vol_fixed;
            if (rm < 0 || rv < 0) continue;
            ll max_xi = q[i];
            if (m[i] > 0) max_xi = min(max_xi, rm / m[i]);
            if (l[i] > 0) max_xi = min(max_xi, rv / l[i]);
            if (max_xi >= 0) {
                ll total_value = value_fixed + max_xi * v[i];
                if (total_value > best_value) {
                    best_value = total_value;
                    for (int k = 0; k < n; ++k)
                        best_counts[k] = (fixed_mask & (1 << k)) ? q[k] : 0;
                    best_counts[i] = max_xi;
                }
            }
        }
    }

    // 3. Two free variables
    for (int mask = 0; mask < total_masks; ++mask) {
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int fixed_mask = mask & ~(1 << i) & ~(1 << j);
                ll mass_fixed = mass_mask[fixed_mask];
                ll vol_fixed = vol_mask[fixed_mask];
                ll value_fixed = value_mask[fixed_mask];
                ll M_res = M - mass_fixed;
                ll L_res = L - vol_fixed;
                if (M_res < 0 || L_res < 0) continue;
                double det = (double)m[i] * l[j] - (double)m[j] * l[i];
                if (fabs(det) < 1e-9) continue;
                double xi_cont = (M_res * l[j] - L_res * m[j]) / det;
                double xj_cont = (m[i] * L_res - l[i] * M_res) / det;
                for (int xi_round = 0; xi_round <= 1; ++xi_round) {
                    ll xi = (xi_round == 0) ? (ll)floor(xi_cont) : (ll)ceil(xi_cont);
                    if (xi < 0) xi = 0;
                    if (xi > q[i]) xi = q[i];
                    for (int xj_round = 0; xj_round <= 1; ++xj_round) {
                        ll xj = (xj_round == 0) ? (ll)floor(xj_cont) : (ll)ceil(xj_cont);
                        if (xj < 0) xj = 0;
                        if (xj > q[j]) xj = q[j];
                        ll mass = mass_fixed + xi * m[i] + xj * m[j];
                        ll volume = vol_fixed + xi * l[i] + xj * l[j];
                        if (mass <= M && volume <= L) {
                            ll total_value = value_fixed + xi * v[i] + xj * v[j];
                            if (total_value > best_value) {
                                best_value = total_value;
                                for (int k = 0; k < n; ++k)
                                    best_counts[k] = (fixed_mask & (1 << k)) ? q[k] : 0;
                                best_counts[i] = xi;
                                best_counts[j] = xj;
                            }
                        }
                    }
                }
            }
        }
    }

    // Try to improve the solution by filling remaining capacity
    ll total_mass = 0, total_vol = 0;
    for (int i = 0; i < n; ++i) {
        total_mass += best_counts[i] * m[i];
        total_vol  += best_counts[i] * l[i];
    }
    ll rm = M - total_mass;
    ll rv = L - total_vol;

    if (rm > 0 && rv > 0) {
        // If remaining capacities are small, use DP
        if (rm <= 2000 && rv <= 2500) {
            vector<Group> groups;
            for (int i = 0; i < n; ++i) {
                ll rq_i = q[i] - best_counts[i];
                if (rq_i <= 0) continue;
                ll k = rq_i;
                for (ll p = 1; p <= k; p <<= 1) {
                    ll take = min(p, k);
                    groups.push_back({ m[i] * take, l[i] * take, v[i] * take, i });
                    k -= take;
                }
            }
            int RM = (int)rm;
            int RV = (int)rv;
            vector<vector<ll>> dp(RM + 1, vector<ll>(RV + 1, -1));
            vector<vector<int>> from_group(RM + 1, vector<int>(RV + 1, -1));
            dp[0][0] = 0;
            for (int g = 0; g < (int)groups.size(); ++g) {
                Group &gr = groups[g];
                if (gr.mass > RM || gr.vol > RV) continue;
                for (int x = RM; x >= gr.mass; --x) {
                    for (int y = RV; y >= gr.vol; --y) {
                        if (dp[x - gr.mass][y - gr.vol] != -1) {
                            ll new_val = dp[x - gr.mass][y - gr.vol] + gr.value;
                            if (new_val > dp[x][y]) {
                                dp[x][y] = new_val;
                                from_group[x][y] = g;
                            }
                        }
                    }
                }
            }
            // Find best additional value
            ll best_add = 0;
            int best_x = 0, best_y = 0;
            for (int x = 0; x <= RM; ++x) {
                for (int y = 0; y <= RV; ++y) {
                    if (dp[x][y] > best_add) {
                        best_add = dp[x][y];
                        best_x = x;
                        best_y = y;
                    }
                }
            }
            if (best_add > 0) {
                vector<ll> add_counts(n, 0);
                int x = best_x, y = best_y;
                while (from_group[x][y] != -1) {
                    int g = from_group[x][y];
                    add_counts[groups[g].type] += groups[g].value / v[groups[g].type];
                    int nx = x - groups[g].mass;
                    int ny = y - groups[g].vol;
                    x = nx; y = ny;
                }
                for (int i = 0; i < n; ++i) {
                    best_counts[i] += add_counts[i];
                    best_value += add_counts[i] * v[i];
                }
            }
        } else {
            // Greedy fill based on value density
            vector<int> indices;
            for (int i = 0; i < n; ++i)
                if (best_counts[i] < q[i]) indices.push_back(i);
            sort(indices.begin(), indices.end(), [&](int a, int b) {
                double den_a = (double)v[a] / ( (double)m[a]/M + (double)l[a]/L );
                double den_b = (double)v[b] / ( (double)m[b]/M + (double)l[b]/L );
                return den_a > den_b;
            });
            vector<ll> temp_counts = best_counts;
            ll temp_mass = total_mass, temp_vol = total_vol;
            ll temp_rm = rm, temp_rv = rv;
            for (int i : indices) {
                ll can_add = min(q[i] - temp_counts[i],
                                 min(temp_rm / m[i], temp_rv / l[i]));
                if (can_add > 0) {
                    temp_counts[i] += can_add;
                    temp_mass += can_add * m[i];
                    temp_vol  += can_add * l[i];
                    temp_rm   -= can_add * m[i];
                    temp_rv   -= can_add * l[i];
                }
            }
            ll temp_value = 0;
            for (int i = 0; i < n; ++i) temp_value += temp_counts[i] * v[i];
            if (temp_value > best_value) {
                best_value = temp_value;
                best_counts = temp_counts;
            }
        }
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << names[i] << "\": " << best_counts[i];
        if (i != n - 1) cout << ",";
        cout << "\n";
    }
    cout << "}\n";

    return 0;
}