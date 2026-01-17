#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

using namespace std;

int n;

bool ask(const vector<int>& indices) {
    cout << "? " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int result;
    cin >> result;
    return result == 1;
}

void answer(const vector<int>& p) {
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    if (n == 2) {
        answer({1, 2});
        return 0;
    }

    vector<int> p(n);
    vector<bool> p1_same_parity(n + 1, false);
    p1_same_parity[1] = true;

    vector<int> group_A = {1}, group_B;

    for (int i = 2; i <= n; ++i) {
        if (ask({1, i})) {
            p1_same_parity[i] = true;
            group_A.push_back(i);
        } else {
            group_B.push_back(i);
        }
    }

    int p1_partner_idx = -1;
    
    // Heuristic to find partner of 1 more efficiently
    if (group_A.size() > 1 && !group_B.empty()) {
        int a2 = group_A[1];
        int k = (group_A.size() > 2 && group_A[2] != 1 && group_A[2] != a2) ? group_A[2] : group_B[0];
        if (k == 1 || k == a2) { // find another k
            for(int i = 1; i <= n; ++i) {
                if (i != 1 && i != a2) {
                    k = i;
                    break;
                }
            }
        }
        
        vector<int> queries1_res_map(n + 1);
        vector<int> queries2_res_map(n + 1);

        for (int b : group_B) {
            queries1_res_map[b] = ask({1, b, k});
        }
        for (int b : group_B) {
            queries2_res_map[b] = ask({a2, b, k});
        }

        for (int b1 : group_B) {
            int partner_of_a2_candidate = -1;
            int count = 0;
            for (int b2 : group_B) {
                if (b1 == b2) continue;
                if (queries1_res_map[b1] == queries2_res_map[b2]) {
                    partner_of_a2_candidate = b2;
                    count++;
                }
            }
            if (count == 1) {
                p1_partner_idx = b1;
                break;
            }
        }
    }
    
    if (p1_partner_idx == -1) {
        // Fallback for small n or if heuristic fails
        p1_partner_idx = group_B[0];
    }
    
    int p1_val_final = -1;
    
    vector<vector<int>> precomputed_mod3_counts(n / 2 + 1, vector<int>(3));
    for (int v = 1; v <= n / 2; ++v) {
        vector<int> s_v;
        for (int i = 1; i <= n; ++i) {
            if (i != v && i != n + 1 - v) {
                s_v.push_back(i);
            }
        }
        for (int val : s_v) {
            precomputed_mod3_counts[v][val % 3]++;
        }
    }
    
    vector<int> q_counts_final(3, 0);
    vector<int> p_mod3(n + 1, -1);
    
    for (int i = 2; i <= n; i++) {
        if (i == p1_partner_idx) continue;
        if (ask({1, p1_partner_idx, i})) {
            int mod_val = (3 - (n + 1) % 3) % 3;
            q_counts_final[mod_val]++;
            p_mod3[i] = mod_val;
        }
    }

    int unknown_count = (n - 2) - (q_counts_final[0] + q_counts_final[1] + q_counts_final[2]);
    for (int v = 1; v <= n / 2; v++) {
        bool match = false;
        if ((n + 1) % 3 == 1) { // remainder 2 is known
            if (q_counts_final[2] == precomputed_mod3_counts[v][2] && unknown_count == precomputed_mod3_counts[v][0] + precomputed_mod3_counts[v][1]) {
                match = true;
            }
        } else if ((n + 1) % 3 == 2) { // remainder 1 is known
            if (q_counts_final[1] == precomputed_mod3_counts[v][1] && unknown_count == precomputed_mod3_counts[v][0] + precomputed_mod3_counts[v][2]) {
                match = true;
            }
        } else { // remainder 0 is known
            if (q_counts_final[0] == precomputed_mod3_counts[v][0] && unknown_count == precomputed_mod3_counts[v][1] + precomputed_mod3_counts[v][2]) {
                match = true;
            }
        }
        if (match) {
            p1_val_final = v;
            break;
        }
    }
    if (p1_val_final == -1) p1_val_final = 1; // Should not happen with correct logic
    
    p[0] = p1_val_final;
    p[p1_partner_idx - 1] = n + 1 - p1_val_final;

    vector<bool> val_used(n + 1, false);
    val_used[p[0]] = true;
    val_used[p[p1_partner_idx - 1]] = true;

    bool p1_val_is_odd = (p[0] % 2 != 0);

    vector<vector<int>> val_groups(6);
    for (int i = 1; i <= n; i++) {
        if (!val_used[i]) {
            val_groups[ (i % 2 != 0)*3 + (i % 3)].push_back(i);
        }
    }
    for(int i=0; i<6; ++i) sort(val_groups[i].rbegin(), val_groups[i].rend());
    
    for (int i = 1; i <= n; i++) {
        if (i == 1 || i == p1_partner_idx) continue;
        if (p_mod3[i] == -1) { // mod 3 was not uniquely determined
            // This part is tricky. A simple guess might not work.
            // But since we have p[1], we know parities of values.
            bool p_i_is_odd = (p1_same_parity[i] == p1_val_is_odd);
            int rem1 = -1, rem2 = -1;
            if ((n+1)%3==1) { rem1=0; rem2=1; }
            else if ((n+1)%3==2) { rem1=0; rem2=2; }
            else { rem1=1; rem2=2; }
            
            int group_idx1 = p_i_is_odd*3 + rem1;
            int group_idx2 = p_i_is_odd*3 + rem2;
            
            if (!val_groups[group_idx1].empty()){
                p_mod3[i] = rem1;
            } else {
                p_mod3[i] = rem2;
            }
        }

        bool p_i_is_odd = (p1_same_parity[i] == p1_val_is_odd);
        int group_idx = p_i_is_odd * 3 + p_mod3[i];
        
        p[i-1] = val_groups[group_idx].back();
        val_groups[group_idx].pop_back();
    }
    
    if (p[0] > n/2) {
        for(int i=0; i<n; ++i) p[i] = n+1-p[i];
    }

    answer(p);

    return 0;
}