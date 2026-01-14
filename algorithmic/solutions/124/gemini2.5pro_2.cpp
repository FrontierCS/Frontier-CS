#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int query(const vector<int>& positions) {
    if (positions.empty()) return 1;
    cout << "? " << positions.size();
    for (int pos : positions) {
        cout << " " << pos;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

void answer(const vector<int>& p) {
    cout << "!";
    for (int val : p) {
        cout << " " << val;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> p(n + 1, 0);
    
    vector<int> odd_indices, even_indices;
    vector<bool> is_odd(n + 1);

    // Determine parity groups relative to p[1]
    vector<int> group_A, group_B;
    group_A.push_back(1);
    for (int i = 2; i <= n; ++i) {
        if (query({1, i}) == 1) {
            group_A.push_back(i);
        } else {
            group_B.push_back(i);
        }
    }

    // Determine which group has odd values
    bool group_A_is_odd;
    if ((n / 2) % 2 != 0) { // n/2 is odd
        if (query(group_A) == 0) {
            group_A_is_odd = true;
        } else {
            group_A_is_odd = false;
        }
    } else { // n/2 is even
        vector<int> q_pos = group_A;
        if (!group_B.empty()) {
            q_pos.push_back(group_B[0]);
        }
        if (query(q_pos) == 0) {
            group_A_is_odd = true;
        } else {
            group_A_is_odd = false;
        }
    }

    if (group_A_is_odd) {
        for (int idx : group_A) is_odd[idx] = true;
        for (int idx : group_B) is_odd[idx] = false;
    } else {
        for (int idx : group_A) is_odd[idx] = false;
        for (int idx : group_B) is_odd[idx] = true;
    }
    
    int u = -1, v = -1;
    if (n > 2) {
        vector<int> all_indices(n);
        iota(all_indices.begin(), all_indices.end(), 1);
        for (int i = 1; i <= n; ++i) {
            vector<int> q_pos;
            for (int j = 1; j <= n; ++j) {
                if (i != j) q_pos.push_back(j);
            }
            if (query(q_pos) == 1) {
                if (u == -1) u = i;
                else v = i;
            }
        }
    } else { // n=2
        u = 1; v = 2;
    }

    bool u_is_1;
    if (is_odd[u]) {
        u_is_1 = true;
    } else {
        u_is_1 = false;
    }

    if (u_is_1) {
        p[u] = 1; p[v] = n;
    } else {
        p[u] = n; p[v] = 1;
    }
    
    vector<bool> assigned(n + 1, false);
    assigned[u] = true;
    assigned[v] = true;

    for (int val = 2; val <= n / 2; ++val) {
        int val_conj = n + 1 - val;
        int first_unassigned = -1;
        for (int i = 1; i <= n; ++i) {
            if (!assigned[i]) {
                first_unassigned = i;
                break;
            }
        }

        int partner = -1;
        for (int i = 1; i <= n; ++i) {
            if (!assigned[i] && i != first_unassigned) {
                bool is_conjugate = true;
                
                bool check3;
                if ((n + 2) % 3 == 0) {
                    check3 = (query({u, first_unassigned, i}) == 1);
                } else {
                    check3 = (query({u, first_unassigned, i}) == 0);
                }
                if (!check3) continue;

                if (n >= 4) {
                    bool check4;
                    if ((2*n + 2) % 4 == 0) {
                        check4 = (query({u, v, first_unassigned, i}) == 1);
                    } else {
                        check4 = (query({u, v, first_unassigned, i}) == 0);
                    }
                    if (!check4) continue;
                }
                
                partner = i;
                break;
            }
        }
        
        assigned[first_unassigned] = true;
        assigned[partner] = true;

        if (is_odd[first_unassigned] == (val % 2 != 0)) {
            p[first_unassigned] = val;
            p[partner] = val_conj;
        } else {
            p[first_unassigned] = val_conj;
            p[partner] = val;
        }
    }

    if (p[1] > n / 2) {
        for (int i = 1; i <= n; ++i) {
            p[i] = n + 1 - p[i];
        }
    }
    
    vector<int> p_to_print;
    for (int i = 1; i <= n; i++) p_to_print.push_back(p[i]);
    answer(p_to_print);

    return 0;
}