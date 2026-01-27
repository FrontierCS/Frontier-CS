#include <bits/stdc++.h>
using namespace std;

static inline bool containsCyclic(const string& T, const string& s) {
    if (T.empty()) return false;
    string TT = T + T;
    size_t pos = TT.find(s);
    if (pos == string::npos) return false;
    return pos < T.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> s(M);
    for (int i = 0; i < M; ++i) cin >> s[i];

    vector<int> order(M);
    iota(order.begin(), order.end(), 0);

    vector<int> uncoveredIdx(M);
    iota(uncoveredIdx.begin(), uncoveredIdx.end(), 0);
    vector<char> alphabet = {'A','B','C','D','E','F','G','H'};

    vector<int> covered(M, 0);

    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto build_row = [&](vector<int>& remaining)->string {
        string T;
        if (!remaining.empty()) {
            // Choose seed among up to K random candidates maximizing immediate coverage in cyclic seed
            int K = min<int>(200, remaining.size());
            vector<int> cand = remaining;
            if ((int)cand.size() > K) {
                shuffle(cand.begin(), cand.end(), rng);
                cand.resize(K);
            }
            int bestIdx = cand[0];
            int bestScore = -1;
            for (int idx : cand) {
                string seed = s[idx];
                string TT = seed + seed;
                int score = 0;
                for (int j : remaining) {
                    if (TT.find(s[j]) != string::npos) ++score;
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestIdx = idx;
                }
            }
            T = s[bestIdx];
        } else {
            // Generic seed
            T = "ABCDEFGH";
        }

        while ((int)T.size() < N) {
            string TT_prev = T + T;
            // Precompute presentPrev for remaining
            int R = remaining.size();
            vector<char> presentPrev(R, 0);
            for (int i = 0; i < R; ++i) {
                if (TT_prev.find(s[remaining[i]]) != string::npos) presentPrev[i] = 1;
            }
            int bestGain = -1;
            char bestChar = 'A';
            for (char c : alphabet) {
                string T2 = T;
                T2.push_back(c);
                string TT2 = T2 + T2;
                int gain = 0;
                for (int i = 0; i < R; ++i) {
                    if (!presentPrev[i]) {
                        if (TT2.find(s[remaining[i]]) != string::npos) ++gain;
                    }
                }
                if (gain > bestGain) {
                    bestGain = gain;
                    bestChar = c;
                }
            }
            if (bestGain <= 0) {
                // Fallback: choose most frequent first character among remaining strings
                array<int, 8> cnt{};
                for (int j : remaining) {
                    char c0 = s[j][0];
                    int idx = c0 - 'A';
                    if (0 <= idx && idx < 8) cnt[idx]++;
                }
                int bestc = 0, bestv = -1;
                for (int i = 0; i < 8; ++i) {
                    if (cnt[i] > bestv) { bestv = cnt[i]; bestc = i; }
                }
                T.push_back(char('A' + bestc));
            } else {
                T.push_back(bestChar);
            }
        }
        return T;
    };

    vector<string> grid(N, string(N, 'A'));

    int rows_built = 0;
    vector<int> remaining;
    remaining.reserve(M);

    for (int i = 0; i < M; ++i) if (!covered[i]) remaining.push_back(i);

    for (int r = 0; r < N; ++r) {
        string row = build_row(remaining);
        // Mark covered
        string TT = row + row;
        vector<int> new_remaining;
        new_remaining.reserve(remaining.size());
        for (int idx : remaining) {
            if (TT.find(s[idx]) != string::npos) {
                covered[idx] = 1;
            } else {
                new_remaining.push_back(idx);
            }
        }
        remaining.swap(new_remaining);
        grid[r] = row;
    }

    for (int i = 0; i < N; ++i) {
        cout << grid[i] << '\n';
    }
    return 0;
}