#include <bits/stdc++.h>
using namespace std;

const int RADIUS = 10000;
const int K_MAX = 100;

struct Point {
    int x, y;
    int iv, ih; // current vertical and horizontal interval indices
};

int N, K;
int a[11]; // a[1..10]
vector<Point> pts;
vector<int> vlines, hlines;
int b[11]; // current b_d
int current_score;

int compute_score(const int b_arr[]) {
    int s = 0;
    for (int d = 1; d <= 10; ++d) s += min(a[d], b_arr[d]);
    return s;
}

// Evaluate adding a vertical line at x = c
pair<int, vector<int>> eval_vertical(int c) {
    vector<int> tmp_v = vlines;
    tmp_v.push_back(c);
    sort(tmp_v.begin(), tmp_v.end());

    map<pair<int,int>, int> cell_cnt;
    for (const auto& p : pts) {
        int iv = upper_bound(tmp_v.begin(), tmp_v.end(), p.x) - tmp_v.begin();
        int ih = p.ih;
        cell_cnt[{iv, ih}]++;
    }

    vector<int> new_b(11, 0);
    for (const auto& it : cell_cnt) {
        int cnt = it.second;
        if (1 <= cnt && cnt <= 10) new_b[cnt]++;
    }
    int score = compute_score(new_b.data());
    return {score, new_b};
}

// Evaluate adding a horizontal line at y = c
pair<int, vector<int>> eval_horizontal(int c) {
    vector<int> tmp_h = hlines;
    tmp_h.push_back(c);
    sort(tmp_h.begin(), tmp_h.end());

    map<pair<int,int>, int> cell_cnt;
    for (const auto& p : pts) {
        int iv = p.iv;
        int ih = upper_bound(tmp_h.begin(), tmp_h.end(), p.y) - tmp_h.begin();
        cell_cnt[{iv, ih}]++;
    }

    vector<int> new_b(11, 0);
    for (const auto& it : cell_cnt) {
        int cnt = it.second;
        if (1 <= cnt && cnt <= 10) new_b[cnt]++;
    }
    int score = compute_score(new_b.data());
    return {score, new_b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> K;
    for (int d = 1; d <= 10; ++d) cin >> a[d];
    pts.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pts[i].x >> pts[i].y;
        pts[i].iv = pts[i].ih = 0;
    }

    // Initial state: no cuts, one cell containing all points
    fill(b, b+11, 0);
    if (N >= 1 && N <= 10) b[N] = 1;
    current_score = compute_score(b);

    for (int iter = 0; iter < K; ++iter) {
        int best_improvement = 0;
        int best_type = -1; // 0 vertical, 1 horizontal
        int best_candidate = 0;
        vector<int> best_new_b;

        // Try vertical candidates
        int V = vlines.size();
        for (int k = 0; k <= V; ++k) {
            // Collect x-coordinates of points in vertical interval k
            vector<int> xs;
            for (const auto& p : pts) if (p.iv == k) xs.push_back(p.x);
            if (xs.empty()) continue;
            sort(xs.begin(), xs.end());

            // Find gaps of size at least 2
            vector<pair<int,int>> gaps;
            for (size_t i = 0; i+1 < xs.size(); ++i) {
                if (xs[i+1] - xs[i] >= 2) {
                    gaps.emplace_back(xs[i], xs[i+1]);
                }
            }
            if (gaps.empty()) continue;

            // Choose the largest gap
            int best_gap = 0;
            for (size_t i = 1; i < gaps.size(); ++i) {
                if (gaps[i].second - gaps[i].first > gaps[best_gap].second - gaps[best_gap].first)
                    best_gap = i;
            }
            int c = (gaps[best_gap].first + gaps[best_gap].second) / 2;
            // Ensure the line cuts the interior of the cake
            if (abs(c) >= RADIUS) continue;
            // Avoid putting a line through any point
            if (binary_search(xs.begin(), xs.end(), c)) continue;
            // Avoid duplicate line
            if (find(vlines.begin(), vlines.end(), c) != vlines.end()) continue;

            auto [score, new_b] = eval_vertical(c);
            int improvement = score - current_score;
            if (improvement >= best_improvement) {
                best_improvement = improvement;
                best_type = 0;
                best_candidate = c;
                best_new_b = new_b;
            }
        }

        // Try horizontal candidates
        int H = hlines.size();
        for (int k = 0; k <= H; ++k) {
            vector<int> ys;
            for (const auto& p : pts) if (p.ih == k) ys.push_back(p.y);
            if (ys.empty()) continue;
            sort(ys.begin(), ys.end());

            vector<pair<int,int>> gaps;
            for (size_t i = 0; i+1 < ys.size(); ++i) {
                if (ys[i+1] - ys[i] >= 2) {
                    gaps.emplace_back(ys[i], ys[i+1]);
                }
            }
            if (gaps.empty()) continue;

            int best_gap = 0;
            for (size_t i = 1; i < gaps.size(); ++i) {
                if (gaps[i].second - gaps[i].first > gaps[best_gap].second - gaps[best_gap].first)
                    best_gap = i;
            }
            int c = (gaps[best_gap].first + gaps[best_gap].second) / 2;
            if (abs(c) >= RADIUS) continue;
            if (binary_search(ys.begin(), ys.end(), c)) continue;
            if (find(hlines.begin(), hlines.end(), c) != hlines.end()) continue;

            auto [score, new_b] = eval_horizontal(c);
            int improvement = score - current_score;
            if (improvement >= best_improvement) {
                best_improvement = improvement;
                best_type = 1;
                best_candidate = c;
                best_new_b = new_b;
            }
        }

        if (best_type == -1) break; // no candidate improves or maintains score

        // Apply the best move
        if (best_type == 0) {
            int c = best_candidate;
            int k = upper_bound(vlines.begin(), vlines.end(), c) - vlines.begin();
            for (auto& p : pts) {
                if (p.iv < k) {
                    // unchanged
                } else if (p.iv == k) {
                    if (p.x < c) p.iv = k;
                    else p.iv = k+1;
                } else {
                    p.iv++;
                }
            }
            vlines.push_back(c);
            sort(vlines.begin(), vlines.end());
        } else {
            int c = best_candidate;
            int k = upper_bound(hlines.begin(), hlines.end(), c) - hlines.begin();
            for (auto& p : pts) {
                if (p.ih < k) {
                    // unchanged
                } else if (p.ih == k) {
                    if (p.y < c) p.ih = k;
                    else p.ih = k+1;
                } else {
                    p.ih++;
                }
            }
            hlines.push_back(c);
            sort(hlines.begin(), hlines.end());
        }

        // Update b and score
        for (int d = 1; d <= 10; ++d) b[d] = best_new_b[d];
        current_score += best_improvement;
    }

    // Output
    int k = vlines.size() + hlines.size();
    cout << k << "\n";
    for (int c : vlines) {
        cout << c << " " << 0 << " " << c << " " << 1 << "\n";
    }
    for (int c : hlines) {
        cout << 0 << " " << c << " " << 1 << " " << c << "\n";
    }

    return 0;
}