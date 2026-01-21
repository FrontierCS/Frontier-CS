#include <bits/stdc++.h>
using namespace std;

static int n, k;
static long long opcnt = 0;

static void do_reset() {
    cout << "R\n";
    cout.flush();
    ++opcnt;
}

static bool do_query(int c) {
    cout << "? " << c << "\n";
    cout.flush();
    ++opcnt;
    char ch;
    if (!(cin >> ch)) exit(0);
    if (ch == 'Y') return true;
    if (ch == 'N') return false;
    exit(0);
}

static vector<int> merge_sets(vector<int> A, vector<int> B) {
    if (A.empty()) return B;
    if (B.empty()) return A;

    // Prefer smaller base when sizes differ; doesn't change correctness.
    if (A.size() > B.size()) swap(A, B);

    if (k == 1) {
        // Fallback (may be too slow for worst-case, but keeps correctness).
        vector<int> res = A;
        for (int b : B) {
            bool dup = false;
            for (int a : res) {
                do_reset();
                (void)do_query(a);
                bool y = do_query(b);
                if (y) {
                    dup = true;
                    break;
                }
            }
            if (!dup) res.push_back(b);
        }
        return res;
    }

    int chunkMax = k / 2;
    if (chunkMax < 1) chunkMax = 1;
    if (chunkMax > k - 1) chunkMax = k - 1;

    vector<int> cand = std::move(B); // distinct representatives
    for (int l = 0; l < (int)A.size() && !cand.empty(); l += chunkMax) {
        int r = min(l + chunkMax, (int)A.size());
        int chunkSize = r - l;
        int t = k - chunkSize; // candidates per batch
        if (t <= 0) t = 1;     // should not happen if chunkSize <= k-1

        vector<char> matched(cand.size(), 0);

        for (int p = 0; p < (int)cand.size(); p += t) {
            do_reset();
            for (int i = l; i < r; i++) (void)do_query(A[i]);

            int end = min(p + t, (int)cand.size());
            for (int j = p; j < end; j++) {
                if (do_query(cand[j])) matched[j] = 1;
            }
        }

        vector<int> nextCand;
        nextCand.reserve(cand.size());
        for (int i = 0; i < (int)cand.size(); i++) {
            if (!matched[i]) nextCand.push_back(cand[i]);
        }
        cand.swap(nextCand);
    }

    A.insert(A.end(), cand.begin(), cand.end());
    return A;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) return 0;

    vector<vector<int>> sets;
    sets.reserve(n / k);

    for (int start = 1; start <= n; start += k) {
        do_reset();
        vector<int> reps;
        reps.reserve(k);
        for (int i = start; i < start + k; i++) {
            bool y = do_query(i);
            if (!y) reps.push_back(i);
        }
        sets.push_back(std::move(reps));
    }

    while (sets.size() > 1) {
        vector<vector<int>> next;
        next.reserve((sets.size() + 1) / 2);
        for (size_t i = 0; i < sets.size(); i += 2) {
            if (i + 1 == sets.size()) {
                next.push_back(std::move(sets[i]));
            } else {
                next.push_back(merge_sets(std::move(sets[i]), std::move(sets[i + 1])));
            }
        }
        sets.swap(next);
    }

    int d = sets.empty() ? 0 : (int)sets[0].size();
    cout << "! " << d << "\n";
    cout.flush();
    return 0;
}