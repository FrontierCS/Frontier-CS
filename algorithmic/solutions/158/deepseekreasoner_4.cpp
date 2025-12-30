#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    int vi, hi; // vertical and horizontal strip indices
};

int getVerticalIndex(int x, const vector<int>& Vlines) {
    return lower_bound(Vlines.begin(), Vlines.end(), x) - Vlines.begin();
}

int getHorizontalIndex(int y, const vector<int>& Hlines) {
    return lower_bound(Hlines.begin(), Hlines.end(), y) - Hlines.begin();
}

int compute_score(const int a[11], const vector<int>& b) {
    int s = 0;
    for (int d = 1; d <= 10; ++d) s += min(a[d], b[d]);
    return s;
}

int findFreeInteger(int start, const set<int>& forbidden, int minVal = -10000, int maxVal = 10000) {
    for (int d = 0; ; ++d) {
        int cand = start + d;
        if (cand >= minVal && cand <= maxVal && !forbidden.count(cand)) return cand;
        cand = start - d;
        if (cand >= minVal && cand <= maxVal && !forbidden.count(cand)) return cand;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    int a[11] = {0};
    for (int d = 1; d <= 10; ++d) cin >> a[d];

    vector<Point> pts(N);
    set<int> x_set, y_set;
    for (int i = 0; i < N; ++i) {
        cin >> pts[i].x >> pts[i].y;
        x_set.insert(pts[i].x);
        y_set.insert(pts[i].y);
    }

    // Fixed number of lines: 50 vertical, 50 horizontal (total 100)
    const int V = 50, H = 50;

    // Generate vertical lines at quantiles of x distribution
    vector<int> xs(N);
    for (int i = 0; i < N; ++i) xs[i] = pts[i].x;
    sort(xs.begin(), xs.end());
    set<int> used_x = x_set;
    vector<int> Vlines;
    for (int i = 1; i <= V; ++i) {
        int pos = i * N / (V + 1);
        if (pos >= N) pos = N - 1;
        int start = xs[pos];
        int cand = findFreeInteger(start, used_x);
        Vlines.push_back(cand);
        used_x.insert(cand);
    }
    sort(Vlines.begin(), Vlines.end());

    // Generate horizontal lines at quantiles of y distribution
    vector<int> ys(N);
    for (int i = 0; i < N; ++i) ys[i] = pts[i].y;
    sort(ys.begin(), ys.end());
    set<int> used_y = y_set;
    vector<int> Hlines;
    for (int i = 1; i <= H; ++i) {
        int pos = i * N / (H + 1);
        if (pos >= N) pos = N - 1;
        int start = ys[pos];
        int cand = findFreeInteger(start, used_y);
        Hlines.push_back(cand);
        used_y.insert(cand);
    }
    sort(Hlines.begin(), Hlines.end());

    // Prepare sorted indices for fast range queries
    vector<int> sorted_x_idx(N), sorted_y_idx(N);
    iota(sorted_x_idx.begin(), sorted_x_idx.end(), 0);
    iota(sorted_y_idx.begin(), sorted_y_idx.end(), 0);
    sort(sorted_x_idx.begin(), sorted_x_idx.end(),
         [&](int i, int j) { return pts[i].x < pts[j].x; });
    sort(sorted_y_idx.begin(), sorted_y_idx.end(),
         [&](int i, int j) { return pts[i].y < pts[j].y; });

    // Initialize strip indices and cell counts
    vector<vector<int>> cell_count(V + 1, vector<int>(H + 1, 0));
    for (Point& p : pts) {
        p.vi = getVerticalIndex(p.x, Vlines);
        p.hi = getHorizontalIndex(p.y, Hlines);
        cell_count[p.vi][p.hi]++;
    }

    // Histogram b[d] = number of cells with exactly d strawberries (1 <= d <= 10)
    vector<int> b(11, 0);
    for (int i = 0; i <= V; ++i)
        for (int j = 0; j <= H; ++j) {
            int c = cell_count[i][j];
            if (c >= 1 && c <= 10) b[c]++;
        }

    int current_score = compute_score(a, b);

    // Local search with hill climbing
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    const int MAX_ITER = 500;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        if (rng() % 2 == 0) {
            // Try moving a vertical line
            int k = rng() % V;
            int old_x = Vlines[k];
            int delta = (rng() % 21) - 10; // -10 .. +10
            if (delta == 0) continue;
            int new_x = old_x + delta;
            int left_bound = (k > 0 ? Vlines[k - 1] : -10000);
            int right_bound = (k + 1 < V ? Vlines[k + 1] : 10000);
            if (new_x <= left_bound || new_x >= right_bound) continue;
            if (used_x.count(new_x)) continue;

            int low_x = min(old_x, new_x);
            int high_x = max(old_x, new_x);
            auto it_low = lower_bound(sorted_x_idx.begin(), sorted_x_idx.end(), low_x,
                [&](int idx, int val) { return pts[idx].x < val; });
            auto it_high = upper_bound(sorted_x_idx.begin(), sorted_x_idx.end(), high_x,
                [&](int val, int idx) { return val < pts[idx].x; });
            vector<int> affected(it_low, it_high);
            if (affected.empty()) continue;

            // Backup state
            auto cell_count_backup = cell_count;
            auto b_backup = b;
            vector<int> old_vi_backup;
            for (int idx : affected) {
                Point& p = pts[idx];
                old_vi_backup.push_back(p.vi);
                int old_c = cell_count[p.vi][p.hi];
                if (old_c <= 10) b[old_c]--;
                cell_count[p.vi][p.hi]--;
                if (old_c - 1 >= 1 && old_c - 1 <= 10) b[old_c - 1]++;

                int new_vi = (p.x < new_x) ? k : k + 1;
                int new_c = cell_count[new_vi][p.hi];
                if (new_c <= 10) b[new_c]--;
                cell_count[new_vi][p.hi]++;
                if (new_c + 1 <= 10) b[new_c + 1]++;

                p.vi = new_vi;
            }

            int new_score = compute_score(a, b);
            if (new_score > current_score) {
                current_score = new_score;
                Vlines[k] = new_x;
                used_x.erase(old_x);
                used_x.insert(new_x);
            } else {
                // Revert
                cell_count = move(cell_count_backup);
                b = move(b_backup);
                int t = 0;
                for (int idx : affected) pts[idx].vi = old_vi_backup[t++];
            }
        } else {
            // Try moving a horizontal line
            int k = rng() % H;
            int old_y = Hlines[k];
            int delta = (rng() % 21) - 10;
            if (delta == 0) continue;
            int new_y = old_y + delta;
            int left_bound = (k > 0 ? Hlines[k - 1] : -10000);
            int right_bound = (k + 1 < H ? Hlines[k + 1] : 10000);
            if (new_y <= left_bound || new_y >= right_bound) continue;
            if (used_y.count(new_y)) continue;

            int low_y = min(old_y, new_y);
            int high_y = max(old_y, new_y);
            auto it_low = lower_bound(sorted_y_idx.begin(), sorted_y_idx.end(), low_y,
                [&](int idx, int val) { return pts[idx].y < val; });
            auto it_high = upper_bound(sorted_y_idx.begin(), sorted_y_idx.end(), high_y,
                [&](int val, int idx) { return val < pts[idx].y; });
            vector<int> affected(it_low, it_high);
            if (affected.empty()) continue;

            auto cell_count_backup = cell_count;
            auto b_backup = b;
            vector<int> old_hi_backup;
            for (int idx : affected) {
                Point& p = pts[idx];
                old_hi_backup.push_back(p.hi);
                int old_c = cell_count[p.vi][p.hi];
                if (old_c <= 10) b[old_c]--;
                cell_count[p.vi][p.hi]--;
                if (old_c - 1 >= 1 && old_c - 1 <= 10) b[old_c - 1]++;

                int new_hi = (p.y < new_y) ? k : k + 1;
                int new_c = cell_count[p.vi][new_hi];
                if (new_c <= 10) b[new_c]--;
                cell_count[p.vi][new_hi]++;
                if (new_c + 1 <= 10) b[new_c + 1]++;

                p.hi = new_hi;
            }

            int new_score = compute_score(a, b);
            if (new_score > current_score) {
                current_score = new_score;
                Hlines[k] = new_y;
                used_y.erase(old_y);
                used_y.insert(new_y);
            } else {
                cell_count = move(cell_count_backup);
                b = move(b_backup);
                int t = 0;
                for (int idx : affected) pts[idx].hi = old_hi_backup[t++];
            }
        }
    }

    // Output the lines
    cout << V + H << '\n';
    for (int c : Vlines) cout << c << " 0 " << c << " 1\n";
    for (int d : Hlines) cout << "0 " << d << " 1 " << d << '\n';

    return 0;
}