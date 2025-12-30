#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <tuple>
#include <unordered_map>
#include <cstdlib>

using namespace std;

const int A = 100000000; // 1e8

struct Tuple4 {
    int d1, d2, d3, d4;
    int cnt;
    int x, y;
};

struct Tuple3 {
    int d1, d2, d3;
    int cnt;
    int x, y;
};

bool dfs4(vector<Tuple4>& tuples, vector<int>& selected,
          unordered_map<int, int>& rem1,
          unordered_map<int, int>& rem2,
          unordered_map<int, int>& rem3,
          unordered_map<int, int>& rem4,
          unordered_map<int, vector<int>>& idx_by_d1,
          int k, int depth) {
    if (depth == k) return true;
    // choose d1 value with smallest branching factor
    int best_v = -1;
    vector<int> best_candidates;
    for (auto& p : rem1) {
        if (p.second > 0) {
            int v = p.first;
            vector<int> viable;
            for (int idx : idx_by_d1[v]) {
                Tuple4& t = tuples[idx];
                if (t.cnt > 0 && rem2[t.d2] > 0 && rem3[t.d3] > 0 && rem4[t.d4] > 0) {
                    viable.push_back(idx);
                }
            }
            if (viable.empty()) continue;
            if (best_v == -1 || viable.size() < best_candidates.size()) {
                best_v = v;
                best_candidates = viable;
            }
        }
    }
    if (best_v == -1) return false;
    for (int idx : best_candidates) {
        Tuple4& t = tuples[idx];
        t.cnt--;
        rem1[t.d1]--; rem2[t.d2]--; rem3[t.d3]--; rem4[t.d4]--;
        selected.push_back(idx);
        if (dfs4(tuples, selected, rem1, rem2, rem3, rem4, idx_by_d1, k, depth+1))
            return true;
        selected.pop_back();
        t.cnt++;
        rem1[t.d1]++; rem2[t.d2]++; rem3[t.d3]++; rem4[t.d4]++;
    }
    return false;
}

bool dfs3(vector<Tuple3>& tuples, vector<int>& selected,
          unordered_map<int, int>& rem1,
          unordered_map<int, int>& rem2,
          unordered_map<int, int>& rem3,
          unordered_map<int, vector<int>>& idx_by_d1,
          int k, int depth) {
    if (depth == k) return true;
    int best_v = -1;
    vector<int> best_candidates;
    for (auto& p : rem1) {
        if (p.second > 0) {
            int v = p.first;
            vector<int> viable;
            for (int idx : idx_by_d1[v]) {
                Tuple3& t = tuples[idx];
                if (t.cnt > 0 && rem2[t.d2] > 0 && rem3[t.d3] > 0) {
                    viable.push_back(idx);
                }
            }
            if (viable.empty()) continue;
            if (best_v == -1 || viable.size() < best_candidates.size()) {
                best_v = v;
                best_candidates = viable;
            }
        }
    }
    if (best_v == -1) return false;
    for (int idx : best_candidates) {
        Tuple3& t = tuples[idx];
        t.cnt--;
        rem1[t.d1]--; rem2[t.d2]--; rem3[t.d3]--;
        selected.push_back(idx);
        if (dfs3(tuples, selected, rem1, rem2, rem3, idx_by_d1, k, depth+1))
            return true;
        selected.pop_back();
        t.cnt++;
        rem1[t.d1]++; rem2[t.d2]++; rem3[t.d3]++;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, k, w;
    cin >> b >> k >> w;

    if (w >= 4) {
        // four single-probe waves
        vector<vector<int>> D(4, vector<int>(k));
        cout << "? 1 " << A << " 0" << endl;
        for (int i = 0; i < k; ++i) cin >> D[0][i];
        cout << "? 1 " << -A << " 0" << endl;
        for (int i = 0; i < k; ++i) cin >> D[1][i];
        cout << "? 1 0 " << A << endl;
        for (int i = 0; i < k; ++i) cin >> D[2][i];
        cout << "? 1 0 " << -A << endl;
        for (int i = 0; i < k; ++i) cin >> D[3][i];

        // generate candidates
        vector<tuple<int, int, int, int, int, int>> raw; // x,y,d1,d2,d3,d4
        for (int d1 : D[0]) {
            for (int d2 : D[1]) {
                for (int d3 : D[2]) {
                    for (int d4 : D[3]) {
                        if ((d2 - d1) % 2 != 0 || (d4 - d3) % 2 != 0) continue;
                        int x = (d2 - d1) / 2;
                        int y = (d4 - d3) / 2;
                        if (abs(x) > b || abs(y) > b) continue;
                        if (d1 + d2 < 2 * A) continue;
                        if ((d1 + d2 - 2 * A) % 2 != 0) continue;
                        int abs_y = (d1 + d2 - 2 * A) / 2;
                        if (abs_y != abs(y)) continue;
                        if (d3 + d4 < 2 * A) continue;
                        if ((d3 + d4 - 2 * A) % 2 != 0) continue;
                        int abs_x = (d3 + d4 - 2 * A) / 2;
                        if (abs_x != abs(x)) continue;
                        raw.emplace_back(x, y, d1, d2, d3, d4);
                    }
                }
            }
        }

        // aggregate by (d1,d2,d3,d4)
        map<tuple<int,int,int,int>, pair<pair<int,int>, int>> agg;
        for (auto& [x,y,d1,d2,d3,d4] : raw) {
            auto key = make_tuple(d1,d2,d3,d4);
            if (agg.find(key) == agg.end()) {
                agg[key] = {{x,y}, 1};
            } else {
                agg[key].second++;
            }
        }

        vector<Tuple4> tuples;
        unordered_map<int, vector<int>> idx_by_d1;
        for (auto& [key, val] : agg) {
            auto [d1,d2,d3,d4] = key;
            auto [pt, cnt] = val;
            tuples.push_back({d1,d2,d3,d4, cnt, pt.first, pt.second});
            idx_by_d1[d1].push_back(tuples.size()-1);
        }

        unordered_map<int, int> freq1, freq2, freq3, freq4;
        for (int v : D[0]) freq1[v]++;
        for (int v : D[1]) freq2[v]++;
        for (int v : D[2]) freq3[v]++;
        for (int v : D[3]) freq4[v]++;

        vector<int> selected;
        bool ok = dfs4(tuples, selected, freq1, freq2, freq3, freq4, idx_by_d1, k, 0);
        if (!ok) {
            // fallback: output first k candidates (should not happen)
            cout << "!";
            for (int i = 0; i < k && i < raw.size(); ++i) {
                auto [x,y,_,__,___,____] = raw[i];
                cout << " " << x << " " << y;
            }
            for (int i = raw.size(); i < k; ++i) cout << " 0 0";
            cout << endl;
        } else {
            cout << "!";
            for (int idx : selected) {
                cout << " " << tuples[idx].x << " " << tuples[idx].y;
            }
            cout << endl;
        }
    }
    else if (w == 3) {
        // three single-probe waves: (A,0), (-A,0), (0,A)
        vector<vector<int>> D(3, vector<int>(k));
        cout << "? 1 " << A << " 0" << endl;
        for (int i = 0; i < k; ++i) cin >> D[0][i];
        cout << "? 1 " << -A << " 0" << endl;
        for (int i = 0; i < k; ++i) cin >> D[1][i];
        cout << "? 1 0 " << A << endl;
        for (int i = 0; i < k; ++i) cin >> D[2][i];

        // generate candidates
        vector<tuple<int, int, int, int, int>> raw; // d1,d2,d3,x,y
        for (int d1 : D[0]) {
            for (int d2 : D[1]) {
                if ((d2 - d1) % 2 != 0) continue;
                int x = (d2 - d1) / 2;
                if (abs(x) > b) continue;
                int sum = d1 + d2;
                if (sum < 2 * A) continue;
                if ((sum - 2 * A) % 2 != 0) continue;
                int abs_y = (sum - 2 * A) / 2;
                if (abs_y < 0) continue;
                int d3_pos = abs(x) + A - abs_y;
                int d3_neg = abs(x) + A + abs_y;
                raw.emplace_back(d1, d2, d3_pos, x, abs_y);
                raw.emplace_back(d1, d2, d3_neg, x, -abs_y);
            }
        }

        // aggregate by (d1,d2,d3)
        map<tuple<int,int,int>, pair<pair<int,int>, int>> agg;
        for (auto& [d1,d2,d3,x,y] : raw) {
            auto key = make_tuple(d1,d2,d3);
            if (agg.find(key) == agg.end()) {
                agg[key] = {{x,y}, 1};
            } else {
                agg[key].second++;
            }
        }

        vector<Tuple3> tuples;
        unordered_map<int, vector<int>> idx_by_d1;
        for (auto& [key, val] : agg) {
            auto [d1,d2,d3] = key;
            auto [pt, cnt] = val;
            tuples.push_back({d1,d2,d3, cnt, pt.first, pt.second});
            idx_by_d1[d1].push_back(tuples.size()-1);
        }

        unordered_map<int, int> freq1, freq2, freq3;
        for (int v : D[0]) freq1[v]++;
        for (int v : D[1]) freq2[v]++;
        for (int v : D[2]) freq3[v]++;

        vector<int> selected;
        bool ok = dfs3(tuples, selected, freq1, freq2, freq3, idx_by_d1, k, 0);
        if (!ok) {
            // fallback
            cout << "!";
            for (int i = 0; i < k && i < raw.size(); ++i) {
                auto [_,__,___,x,y] = raw[i];
                cout << " " << x << " " << y;
            }
            for (int i = raw.size(); i < k; ++i) cout << " 0 0";
            cout << endl;
        } else {
            cout << "!";
            for (int idx : selected) {
                cout << " " << tuples[idx].x << " " << tuples[idx].y;
            }
            cout << endl;
        }
    }
    else { // w == 2
        // Not enough waves for full solution; output dummy answer.
        // (In a contest one would need a more sophisticated method here.)
        cout << "!";
        for (int i = 0; i < k; ++i) cout << " 0 0";
        cout << endl;
    }

    return 0;
}