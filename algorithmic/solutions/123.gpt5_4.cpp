#include <bits/stdc++.h>
using namespace std;

// Interactive helper functions
static int Q_LIMIT = 53;
static int G_LIMIT = 2;

bool ask(const vector<int>& S) {
    if (S.empty()) {
        // Should not happen; but to avoid protocol violation, ask a dummy singleton "1"
        cout << "? 1 1" << endl;
        cout.flush();
    } else {
        cout << "? " << S.size();
        for (int x : S) cout << ' ' << x;
        cout << endl;
        cout.flush();
    }
    string ans;
    if (!(cin >> ans)) exit(0);
    return ans[0] == 'Y' || ans[0] == 'y';
}

void guess(int x) {
    cout << "! " << x << endl;
    cout.flush();
    string res;
    if (!(cin >> res)) exit(0);
    if (res == ":)") exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 1);

    auto do_round = [&](int m) {
        int K = (int)cand.size();
        if (K <= 2 || m <= 0) return;

        int codesCount = 1 << m;
        vector<vector<int>> groups(codesCount);

        // Choose K code indices spread as uniformly as possible across [0, 2^m)
        // Use rounding to nearest to distribute evenly
        vector<int> codeIdx(K);
        for (int t = 0; t < K; ++t) {
            long long num = 1LL * t * codesCount + K / 2;
            int code = (int)(num / K);
            if (code < 0) code = 0;
            if (code >= codesCount) code = codesCount - 1;
            codeIdx[t] = code;
        }
        // Ensure extremes are covered to help avoid empty S_i
        if (K >= 1) codeIdx[0] = 0;
        if (K >= 2) codeIdx[K - 1] = codesCount - 1;

        for (int i = 0; i < K; ++i) {
            groups[codeIdx[i]].push_back(cand[i]);
        }

        // Build and ask m queries
        vector<int> a(m, 0);
        for (int i = 0; i < m; ++i) {
            vector<int> S;
            for (int j = 0; j < codesCount; ++j) {
                if ((j >> i) & 1) {
                    if (!groups[j].empty()) {
                        S.insert(S.end(), groups[j].begin(), groups[j].end());
                    }
                }
            }
            if (S.empty()) {
                // Ensure non-empty set: pick one element (any)
                // Fallback: take from the largest non-empty group
                for (int j = 0; j < codesCount; ++j) {
                    if (!groups[j].empty()) {
                        S.push_back(groups[j].back());
                        break;
                    }
                }
            }
            bool ans = ask(S);
            a[i] = ans ? 1 : 0;
        }

        // Keep candidates whose code is consistent:
        // For all i, not ((b_i != a_i) and (b_{i+1} != a_{i+1}))
        vector<int> nextCand;
        nextCand.reserve(cand.size());
        for (int j = 0; j < codesCount; ++j) {
            if (groups[j].empty()) continue;
            bool ok = true;
            for (int i = 0; i + 1 < m; ++i) {
                int bi = (j >> i) & 1;
                int bi1 = (j >> (i + 1)) & 1;
                if ((bi != a[i]) && (bi1 != a[i + 1])) { ok = false; break; }
            }
            if (ok) {
                nextCand.insert(nextCand.end(), groups[j].begin(), groups[j].end());
            }
        }
        cand.swap(nextCand);
    };

    // Pre-planned schedule to stay within 53 questions while aggressively shrinking
    // This plan aims to reduce candidates very fast with few large rounds.
    vector<int> schedule;

    // Choose schedule dynamically depending on n to avoid waste for small n
    // Try to use up to 53 questions with around 4 rounds.
    if (n <= 3) {
        // Directly guess up to two values
        if (n >= 1) guess(1);
        if (n >= 2) guess(2);
        // If still not done, guess 3 as last resort (though G_LIMIT=2, but just in case)
        // Not allowed; so return.
        return 0;
    } else {
        // Prefer large m's summing to 53
        // Common plan: {16,14,13,10} -> total 53
        schedule = {16, 14, 13, 10};
    }

    int usedQ = 0;
    for (int m : schedule) {
        if ((int)cand.size() <= 2) break;
        if (usedQ + m > Q_LIMIT) break;
        do_round(m);
        usedQ += m;
    }

    // If still too many candidates and we have remaining questions, try smaller adaptive rounds
    while ((int)cand.size() > 2 && usedQ < Q_LIMIT) {
        // Choose m to use remaining budget efficiently
        int rem = Q_LIMIT - usedQ;
        int m = min(14, rem); // bound m to avoid too large memory
        // Ensure m at least 2
        if (m < 2) m = rem;
        if (m <= 0) break;
        do_round(m);
        usedQ += m;
    }

    // Finalize with guesses
    if (cand.empty()) {
        // If somehow empty, just guess 1 to comply
        guess(1);
        return 0;
    }
    if ((int)cand.size() == 1) {
        guess(cand[0]);
        return 0;
    }
    // Up to 2 guesses:
    // Try first two candidates
    guess(cand[0]);
    if ((int)cand.size() >= 2) guess(cand[1]);
    // If still not done, try the remaining (won't be allowed by G_LIMIT, but program ends anyway)
    return 0;
}