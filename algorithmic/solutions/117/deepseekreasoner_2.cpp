#include <bits/stdc++.h>
using namespace std;

const double EPS = 1e-6;
const double INF = 1e18;

map<pair<int, int>, double> cache;

double query(int x, int y) {
    auto key = make_pair(x, y);
    if (cache.find(key) != cache.end()) return cache[key];
    cout << "? " << x << " " << y << endl;
    double res;
    cin >> res;
    return cache[key] = res;
}

// Given x and range [L, R] (integers), find all breakpoints (y, delta)
// where delta = D(y) - D(y-1) = 2 * total weight of lines with y_i = y.
vector<pair<int, double>> get_breakpoints(int x, int L, int R) {
    vector<pair<int, double>> breaks;
    // We'll start from left of L
    int cur = L - 1;
    // Get D(cur) = f(cur+1) - f(cur)
    double f_cur = query(x, cur);
    double f_next = query(x, cur + 1);
    double Dcur = f_next - f_cur;
    while (true) {
        // Check if there is any breakpoint left
        double f_R = query(x, R);
        double f_R1 = query(x, R + 1);
        double DR = f_R1 - f_R;
        if (abs(DR - Dcur) < EPS) break; // no more breakpoints
        int lo = cur, hi = R;
        while (hi - lo > 1) {
            int mid = (lo + hi) / 2;
            double f_mid = query(x, mid);
            double f_mid1 = query(x, mid + 1);
            double Dmid = f_mid1 - f_mid;
            if (Dmid > Dcur + EPS) {
                hi = mid;
            } else {
                lo = mid;
            }
        }
        // breakpoint at y = hi
        double f_hi = query(x, hi);
        double f_hi1 = query(x, hi + 1);
        double Dhi = f_hi1 - f_hi;
        double delta = Dhi - Dcur;
        breaks.emplace_back(hi, delta);
        cur = hi;
        Dcur = Dhi;
    }
    return breaks;
}

int main() {
    int n;
    cin >> n;
    // For x = 0, breakpoints are b_i in [-10000, 10000]
    auto breaks0 = get_breakpoints(0, -10000, 10000);
    // For x = 1, breakpoints are a_i + b_i in [-20000, 20000]
    auto breaks1 = get_breakpoints(1, -20000, 20000);

    // Each breakpoint in breaks1 corresponds to one line with weight w = delta/2
    struct Candidate {
        double w;
        int y1; // at x=1
    };
    vector<Candidate> cands;
    for (auto &p : breaks1) {
        cands.push_back({p.second / 2.0, p.first});
    }

    // Buckets for x=0: each bucket has b and remaining weight (total weight of lines with that b)
    struct Bucket {
        int b;
        double rem_weight;
    };
    vector<Bucket> buckets;
    for (auto &p : breaks0) {
        buckets.push_back({p.first, p.second / 2.0});
    }

    // Sort candidates by weight descending (heuristic)
    sort(cands.begin(), cands.end(), [](const Candidate &a, const Candidate &b) {
        return a.w > b.w;
    });

    vector<pair<int, int>> lines; // (a, b)
    vector<bool> used(buckets.size(), false);

    for (auto &cand : cands) {
        double w = cand.w;
        int y1 = cand.y1;
        int best_b = -1;
        double best_diff = INF;
        for (int i = 0; i < (int)buckets.size(); i++) {
            if (buckets[i].rem_weight < w - EPS) continue;
            int b = buckets[i].b;
            int a = y1 - b;
            if (a < -10000 || a > 10000) continue;
            double w_exact = 1.0 / sqrt(1.0 + a * (long long)a);
            if (abs(w_exact - w) > EPS) continue;
            // candidate fits
            double diff = abs(buckets[i].rem_weight - w);
            if (diff < best_diff) {
                best_diff = diff;
                best_b = i;
            }
        }
        if (best_b == -1) {
            // Should not happen if data is consistent
            continue;
        }
        int b = buckets[best_b].b;
        int a = y1 - b;
        lines.emplace_back(a, b);
        buckets[best_b].rem_weight -= w;
        if (buckets[best_b].rem_weight < EPS) buckets[best_b].rem_weight = 0;
    }

    // Output answer
    cout << "!";
    for (auto &line : lines) {
        cout << " " << line.first;
    }
    for (auto &line : lines) {
        cout << " " << line.second;
    }
    cout << endl;

    return 0;
}