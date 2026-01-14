#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

struct State {
    int u1, u2;
    int d1, d2;
    int score;
    int prev_idx;
    int move; // 0:a(u1), 1:c(u2), 2:b(d1), 3:d(d2)
};

struct StepInfo {
    int prev_idx;
    int move;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Beam width
    // With N=100,000, we need to be careful with complexity.
    // W=80 implies roughly 3-4 * 10^8 operations, which fits within 1-2s.
    int W = 80;

    vector<State> curr;
    curr.reserve(W);
    // Initial state: u1=u2=0, d1=d2=n+1
    curr.push_back({0, 0, n + 1, n + 1, 0, -1, -1});

    vector<vector<StepInfo>> history(n);

    vector<State> next_cands;
    next_cands.reserve(W * 8); 

    for (int k = 0; k < n; ++k) {
        int x = p[k];
        next_cands.clear();

        for (int i = 0; i < (int)curr.size(); ++i) {
            const auto& s = curr[i];
            bool extended = false;

            // Try extending Inc1 (a)
            if (x > s.u1) {
                next_cands.push_back({x, s.u2, s.d1, s.d2, s.score + 1, i, 0});
                extended = true;
            }
            // Try extending Inc2 (c)
            if (x > s.u2) {
                next_cands.push_back({s.u1, x, s.d1, s.d2, s.score + 1, i, 1});
                extended = true;
            }
            // Try extending Dec1 (b)
            if (x < s.d1) {
                next_cands.push_back({s.u1, s.u2, x, s.d2, s.score + 1, i, 2});
                extended = true;
            }
            // Try extending Dec2 (d)
            if (x < s.d2) {
                next_cands.push_back({s.u1, s.u2, s.d1, x, s.score + 1, i, 3});
                extended = true;
            }

            if (!extended) {
                // No valid extension, must reset one bucket
                next_cands.push_back({x, s.u2, s.d1, s.d2, s.score, i, 0});
                next_cands.push_back({s.u1, x, s.d1, s.d2, s.score, i, 1});
                next_cands.push_back({s.u1, s.u2, x, s.d2, s.score, i, 2});
                next_cands.push_back({s.u1, s.u2, s.d1, x, s.score, i, 3});
            }
        }

        // Sort candidates
        // Criteria: Score DESC, Openness DESC, then canonical endpoints for dedup grouping
        sort(next_cands.begin(), next_cands.end(), [](const State& a, const State& b) {
            if (a.score != b.score) return a.score > b.score;
            
            int open_a = a.d1 + a.d2 - a.u1 - a.u2;
            int open_b = b.d1 + b.d2 - b.u1 - b.u2;
            if (open_a != open_b) return open_a > open_b;

            // Canonical comparison for grouping
            int au1 = min(a.u1, a.u2), au2 = max(a.u1, a.u2);
            int bu1 = min(b.u1, b.u2), bu2 = max(b.u1, b.u2);
            if (au1 != bu1) return au1 < bu1;
            if (au2 != bu2) return au2 < bu2;

            int ad1 = min(a.d1, a.d2), ad2 = max(a.d1, a.d2);
            int bd1 = min(b.d1, b.d2), bd2 = max(b.d1, b.d2);
            if (ad1 != bd1) return ad1 < bd1;
            return ad2 < bd2;
        });

        curr.clear();
        // Dedup and fill curr
        for (const auto& cand : next_cands) {
            if (curr.size() >= W) break;
            
            if (!curr.empty()) {
                const auto& last = curr.back();
                int lu1 = min(last.u1, last.u2), lu2 = max(last.u1, last.u2);
                int cu1 = min(cand.u1, cand.u2), cu2 = max(cand.u1, cand.u2);
                int ld1 = min(last.d1, last.d2), ld2 = max(last.d1, last.d2);
                int cd1 = min(cand.d1, cand.d2), cd2 = max(cand.d1, cand.d2);

                if (lu1 == cu1 && lu2 == cu2 && ld1 == cd1 && ld2 == cd2) {
                    continue;
                }
            }
            curr.push_back(cand);
        }

        history[k].resize(curr.size());
        for (int i = 0; i < (int)curr.size(); ++i) {
            history[k][i] = {curr[i].prev_idx, curr[i].move};
        }
    }

    // Reconstruct solution
    int idx = 0; // The first state in curr is the best
    vector<int> moves(n);
    for (int k = n - 1; k >= 0; --k) {
        moves[k] = history[k][idx].move;
        idx = history[k][idx].prev_idx;
    }

    vector<int> a, b, c, d_seq;
    a.reserve(n); b.reserve(n); c.reserve(n); d_seq.reserve(n);

    for (int k = 0; k < n; ++k) {
        if (moves[k] == 0) a.push_back(p[k]);
        else if (moves[k] == 1) c.push_back(p[k]);
        else if (moves[k] == 2) b.push_back(p[k]);
        else d_seq.push_back(p[k]);
    }

    cout << a.size() << " " << b.size() << " " << c.size() << " " << d_seq.size() << "\n";
    for (int i = 0; i < (int)a.size(); ++i) cout << a[i] << (i == a.size() - 1 ? "" : " "); cout << "\n";
    for (int i = 0; i < (int)b.size(); ++i) cout << b[i] << (i == b.size() - 1 ? "" : " "); cout << "\n";
    for (int i = 0; i < (int)c.size(); ++i) cout << c[i] << (i == c.size() - 1 ? "" : " "); cout << "\n";
    for (int i = 0; i < (int)d_seq.size(); ++i) cout << d_seq[i] << (i == d_seq.size() - 1 ? "" : " "); cout << "\n";

    return 0;
}