#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Using 0-based indexing internally
int ask(int i, int j) {
    cout << "? " << i + 1 << " " << j + 1 << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result;
}

void answer(const vector<int>& p) {
    cout << "! ";
    for (size_t i = 0; i < p.size(); ++i) {
        cout << p[i] << (i == p.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> p(n);
    
    int pivot_idx = 0;
    vector<int> or_with_pivot(n);

    for (int i = 1; i < n; ++i) {
        or_with_pivot[i] = ask(pivot_idx, i);
    }
    
    int p_pivot_val = 0;
    for (int k = 0; k < 12; ++k) {
        bool all_one = true;
        for (int i = 1; i < n; ++i) {
            if (((or_with_pivot[i] >> k) & 1) == 0) {
                all_one = false;
                break;
            }
        }
        if (all_one) {
            p_pivot_val |= (1 << k);
        }
    }
    
    p[pivot_idx] = p_pivot_val;
    
    set<int> remaining_values;
    for (int i = 0; i < n; ++i) {
        if (i != p[pivot_idx]) {
            remaining_values.insert(i);
        }
    }

    map<int, vector<int>> groups_by_or;
    for (int i = 1; i < n; ++i) {
        groups_by_or[or_with_pivot[i]].push_back(i);
    }

    for (auto const& [or_val, indices] : groups_by_or) {
        if (indices.size() == 1) {
            int current_idx = indices[0];
            for (int val : remaining_values) {
                if ((p[pivot_idx] | val) == or_val) {
                    p[current_idx] = val;
                    remaining_values.erase(val);
                    break;
                }
            }
        }
    }

    for (auto const& [or_val, indices] : groups_by_or) {
        if (indices.size() > 1) {
            vector<int> cand_values;
            for (int val : remaining_values) {
                if ((p[pivot_idx] | val) == or_val) {
                    cand_values.push_back(val);
                }
            }

            int group_pivot_idx = indices[0];
            vector<int> or_pivot_group(indices.size());

            for (size_t i = 1; i < indices.size(); ++i) {
                or_pivot_group[i] = ask(group_pivot_idx, indices[i]);
            }

            for (int val_cand : cand_values) {
                vector<int> p_group;
                p_group.push_back(val_cand);
                bool possible = true;
                set<int> used_in_group;
                used_in_group.insert(val_cand);

                for (size_t i = 1; i < indices.size(); ++i) {
                    int needed_or = or_pivot_group[i];
                    int found_match = -1;
                    for (int v : cand_values) {
                        if (used_in_group.count(v)) continue;
                        if ((val_cand | v) == needed_or) {
                            if (found_match != -1) { 
                                found_match = -2;
                                break;
                            }
                            found_match = v;
                        }
                    }
                    if (found_match >= 0) {
                        used_in_group.insert(found_match);
                    } else {
                        possible = false;
                        break;
                    }
                }

                if (possible) {
                    p[group_pivot_idx] = val_cand;
                    used_in_group.clear();
                    used_in_group.insert(val_cand);
                    for (size_t i = 1; i < indices.size(); ++i) {
                        int needed_or = or_pivot_group[i];
                        for (int v : cand_values) {
                            if (used_in_group.count(v)) continue;
                            if ((p[group_pivot_idx] | v) == needed_or) {
                                p[indices[i]] = v;
                                used_in_group.insert(v);
                                break;
                            }
                        }
                    }
                    for(int idx : indices){
                        remaining_values.erase(p[idx]);
                    }
                    break;
                }
            }
        }
    }

    answer(p);

    return 0;
}