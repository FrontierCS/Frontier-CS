#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <cstdint>
#include <array>
#include <cmath>

using namespace std;

struct Point {
    int x, y;
};

int N, K;
int a[11];                 // a[1]..a[10]
vector<Point> pts;         // all strawberries

unordered_set<int> used_x, used_y;

// hash for pair<uint64_t, uint64_t>
struct pair_hash {
    size_t operator()(const pair<uint64_t, uint64_t>& p) const {
        return hash<uint64_t>{}(p.first) ^ (hash<uint64_t>{}(p.second) << 1);
    }
};

// compute score for given sets of vertical lines (x = c) and horizontal lines (y = d)
int compute_score(const vector<int>& vert, const vector<int>& horiz) {
    unordered_map<pair<uint64_t, uint64_t>, int, pair_hash> cnt;
    int V = vert.size();
    int H = horiz.size();
    for (const Point& p : pts) {
        uint64_t vmask = 0;
        for (int i = 0; i < V; ++i) {
            if (p.x > vert[i])
                vmask |= (1ULL << i);
        }
        uint64_t hmask = 0;
        for (int i = 0; i < H; ++i) {
            if (p.y > horiz[i])
                hmask |= (1ULL << i);
        }
        cnt[{vmask, hmask}]++;
    }
    int b[11] = {0};
    for (const auto& entry : cnt) {
        int s = entry.second;
        if (s >= 1 && s <= 10)
            b[s]++;
    }
    int score = 0;
    for (int d = 1; d <= 10; ++d)
        score += min(a[d], b[d]);
    return score;
}

// try to place V vertical and H horizontal lines, store them in vert/horiz
void try_place_lines(int V, int H, vector<int>& vert, vector<int>& horiz) {
    vert.clear();
    horiz.clear();
    if (V > 0) {
        // sort by x
        vector<Point> pts_x = pts;
        sort(pts_x.begin(), pts_x.end(),
             [](const Point& p, const Point& q) { return p.x < q.x; });
        int prev_idx = -1;
        unordered_set<int> added; // avoid duplicate lines
        for (int i = 1; i <= V; ++i) {
            int idx = (i * N) / (V + 1);
            if (idx <= 0 || idx >= N || idx == prev_idx)
                continue;
            prev_idx = idx;
            int xl = pts_x[idx - 1].x;
            int xr = pts_x[idx].x;
            if (xl >= xr)
                continue;
            // look for an integer c between xl and xr not used by any point
            int c = -1;
            for (int cand = xl + 1; cand < xr; ++cand) {
                if (used_x.find(cand) == used_x.end()) {
                    c = cand;
                    break;
                }
            }
            if (c == -1) {
                // no integer strictly between, search around the middle
                int desired = (xl + xr) / 2;
                for (int d = 0; d <= 1000; ++d) {
                    int cand1 = desired + d;
                    int cand2 = desired - d;
                    if (cand1 >= -10000 && cand1 <= 10000 && used_x.find(cand1) == used_x.end()) {
                        c = cand1;
                        break;
                    }
                    if (cand2 >= -10000 && cand2 <= 10000 && used_x.find(cand2) == used_x.end()) {
                        c = cand2;
                        break;
                    }
                }
            }
            if (c != -1 && added.find(c) == added.end()) {
                vert.push_back(c);
                added.insert(c);
            }
        }
    }
    if (H > 0) {
        // sort by y
        vector<Point> pts_y = pts;
        sort(pts_y.begin(), pts_y.end(),
             [](const Point& p, const Point& q) { return p.y < q.y; });
        int prev_idx = -1;
        unordered_set<int> added;
        for (int i = 1; i <= H; ++i) {
            int idx = (i * N) / (H + 1);
            if (idx <= 0 || idx >= N || idx == prev_idx)
                continue;
            prev_idx = idx;
            int yl = pts_y[idx - 1].y;
            int yr = pts_y[idx].y;
            if (yl >= yr)
                continue;
            int d = -1;
            for (int cand = yl + 1; cand < yr; ++cand) {
                if (used_y.find(cand) == used_y.end()) {
                    d = cand;
                    break;
                }
            }
            if (d == -1) {
                int desired = (yl + yr) / 2;
                for (int diff = 0; diff <= 1000; ++diff) {
                    int cand1 = desired + diff;
                    int cand2 = desired - diff;
                    if (cand1 >= -10000 && cand1 <= 10000 && used_y.find(cand1) == used_y.end()) {
                        d = cand1;
                        break;
                    }
                    if (cand2 >= -10000 && cand2 <= 10000 && used_y.find(cand2) == used_y.end()) {
                        d = cand2;
                        break;
                    }
                }
            }
            if (d != -1 && added.find(d) == added.end()) {
                horiz.push_back(d);
                added.insert(d);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // input
    cin >> N >> K;
    for (int d = 1; d <= 10; ++d)
        cin >> a[d];
    pts.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pts[i].x >> pts[i].y;
        used_x.insert(pts[i].x);
        used_y.insert(pts[i].y);
    }

    int best_score = -1;
    vector<array<int, 4>> best_lines;

    // try several splits of the 100 lines into vertical and horizontal
    for (int V = 0; V <= 100; V += 10) {
        int H = 100 - V;
        vector<int> vert, horiz;
        try_place_lines(V, H, vert, horiz);
        // build lines for output
        vector<array<int, 4>> lines;
        for (int c : vert)
            lines.push_back({c, 0, c, 1});
        for (int d : horiz)
            lines.push_back({0, d, 1, d});
        if (lines.size() > K) // should not happen
            continue;
        int score = compute_score(vert, horiz);
        if (score > best_score) {
            best_score = score;
            best_lines = lines;
        }
    }

    // output the best found solution
    cout << best_lines.size() << "\n";
    for (const auto& line : best_lines) {
        cout << line[0] << " " << line[1] << " "
             << line[2] << " " << line[3] << "\n";
    }

    return 0;
}