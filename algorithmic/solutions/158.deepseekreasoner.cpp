#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <cmath>
#include <climits>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K; // K is always 100, but we read it

    vector<int> a(11, 0);
    for (int d = 1; d <= 10; ++d) {
        cin >> a[d];
    }

    vector<pair<int, int>> berries(N);
    unordered_set<int> xset, yset;
    int min_x = INT_MAX, max_x = INT_MIN;
    int min_y = INT_MAX, max_y = INT_MIN;

    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
        berries[i] = {x, y};
        xset.insert(x);
        yset.insert(y);
        min_x = min(min_x, x);
        max_x = max(max_x, x);
        min_y = min(min_y, y);
        max_y = max(max_y, y);
    }

    // Expand the range slightly to avoid placing lines exactly at strawberries
    min_x--; max_x++;
    min_y--; max_y++;

    // Precompute vertical and horizontal lines for each possible count (0..100)
    vector<vector<int>> vlines(101), hlines(101);

    auto computeLines = [](int num, int minv, int maxv, const unordered_set<int>& forbid) -> vector<int> {
        vector<int> res;
        if (num == 0) return res;
        double step = (maxv - minv) / (num + 1.0);
        int prev = minv - 1; // ensure lines are strictly increasing
        for (int i = 1; i <= num; ++i) {
            double target = minv + i * step;
            int cand = round(target);
            int start = max(cand, prev + 1);
            int c = -1;
            // Search for an integer not in forbid, starting from 'start'
            for (int offset = 0; offset <= 10000; ++offset) {
                int candidate = start + offset;
                if (forbid.find(candidate) == forbid.end()) {
                    c = candidate;
                    break;
                }
            }
            if (c == -1) {
                // Cannot find a suitable line; stop adding more lines for this count
                break;
            }
            res.push_back(c);
            prev = c;
        }
        return res;
    };

    for (int V = 1; V <= 100; ++V) {
        vlines[V] = computeLines(V, min_x, max_x, xset);
    }
    vlines[0] = {};

    for (int H = 1; H <= 100; ++H) {
        hlines[H] = computeLines(H, min_y, max_y, yset);
    }
    hlines[0] = {};

    // Evaluate all pairs (V, H) such that V + H <= 100
    int best_score = -1;
    int best_V = 0, best_H = 0;
    vector<int> best_v, best_h;

    for (int V = 0; V <= 100; ++V) {
        for (int H = 0; H <= 100 - V; ++H) {
            const vector<int>& vl = vlines[V];
            const vector<int>& hl = hlines[H];
            int actualV = vl.size();
            int actualH = hl.size();
            int num_v_intervals = actualV + 1;
            int num_h_intervals = actualH + 1;

            unordered_map<int, int> cell_counts;
            for (const auto& berry : berries) {
                int x = berry.first, y = berry.second;
                int i = 0, j = 0;
                if (actualV > 0) {
                    auto it = upper_bound(vl.begin(), vl.end(), x);
                    i = it - vl.begin();
                }
                if (actualH > 0) {
                    auto it = upper_bound(hl.begin(), hl.end(), y);
                    j = it - hl.begin();
                }
                int key = i * num_h_intervals + j;
                cell_counts[key]++;
            }

            vector<int> b(11, 0);
            for (const auto& p : cell_counts) {
                int cnt = p.second;
                if (cnt >= 1 && cnt <= 10) {
                    b[cnt]++;
                }
            }

            int score = 0;
            for (int d = 1; d <= 10; ++d) {
                score += min(a[d], b[d]);
            }

            if (score > best_score) {
                best_score = score;
                best_V = V;
                best_H = H;
                best_v = vl;
                best_h = hl;
            }
        }
    }

    // Output the best solution
    int k = best_v.size() + best_h.size();
    cout << k << "\n";
    for (int x : best_v) {
        cout << x << " " << -1000000000 << " " << x << " " << 1000000000 << "\n";
    }
    for (int y : best_h) {
        cout << -1000000000 << " " << y << " " << 1000000000 << " " << y << "\n";
    }

    return 0;
}