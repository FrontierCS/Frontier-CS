#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int orig_n = n, orig_m = m;
    bool transpose_flag = false;
    if (orig_n > orig_m) {
        swap(orig_n, orig_m);
        transpose_flag = true;
    }
    int nn = orig_n;
    int mm = orig_m;
    vector<vector<int>> row_sets(nn + 1);
    vector<vector<int>> col_rows(mm + 1);
    int sq = 0;
    for (int i = 0; i * i <= mm; ++i) {
        sq = i;
    }
    int base = mm / nn;
    int target_d = base + sq;
    for (int r = 1; r <= nn; ++r) {
        vector<pair<int, int>> candidates;
        for (int c = 1; c <= mm; ++c) {
            int deg = col_rows[c].size();
            candidates.emplace_back(deg, c);
        }
        sort(candidates.begin(), candidates.end());
        vector<bool> used(nn + 1, false);
        vector<int> Sr;
        for (auto& p : candidates) {
            int c = p.second;
            if ((int)Sr.size() >= target_d) continue;
            bool can = true;
            for (int pp : col_rows[c]) {
                if (used[pp]) {
                    can = false;
                    break;
                }
            }
            if (can) {
                Sr.push_back(c);
                for (int pp : col_rows[c]) {
                    used[pp] = true;
                }
            }
        }
        row_sets[r] = std::move(Sr);
        for (int c : row_sets[r]) {
            col_rows[c].push_back(r);
        }
    }
    vector<pair<int, int>> points;
    for (int i = 1; i <= nn; ++i) {
        for (int j : row_sets[i]) {
            if (transpose_flag) {
                points.emplace_back(j, i);
            } else {
                points.emplace_back(i, j);
            }
        }
    }
    cout << points.size() << endl;
    for (auto& pr : points) {
        cout << pr.first << " " << pr.second << endl;
    }
    return 0;
}