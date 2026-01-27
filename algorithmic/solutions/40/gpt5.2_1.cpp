#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    int queries = 0;

    long long ask(const vector<int>& idx) {
        ++queries;
        if (queries > 200) exit(0);
        cout << "0 " << idx.size();
        for (int x : idx) cout << ' ' << x;
        cout << '\n';
        cout.flush();

        long long res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    }

    static long long tri(int w) {
        return 1LL * w * (w + 1) / 2;
    }

    vector<int> buildExistQuery(int pivot, const vector<int>& subset) {
        vector<int> idx;
        idx.reserve(3 * subset.size());
        for (int j : subset) {
            idx.push_back(pivot);
            idx.push_back(j);
            idx.push_back(pivot);
        }
        return idx;
    }

    void solveCase() {
        int pivot = 1;

        // Find an index "diff" such that s[diff] != s[pivot]
        vector<int> candidates;
        candidates.reserve(max(0, n - 1));
        for (int i = 2; i <= n; i++) candidates.push_back(i);

        int chunkSize = 333;
        vector<int> chunk;
        bool foundChunk = false;
        for (int start = 0; start < (int)candidates.size(); start += chunkSize) {
            int end = min((int)candidates.size(), start + chunkSize);
            chunk.assign(candidates.begin() + start, candidates.begin() + end);
            auto qidx = buildExistQuery(pivot, chunk);
            long long res = ask(qidx);
            if (res > 0) {
                foundChunk = true;
                break;
            }
        }
        if (!foundChunk) exit(0);

        // Binary search inside chunk to find a differing index
        vector<int> cur = chunk;
        while ((int)cur.size() > 1) {
            int mid = (int)cur.size() / 2;
            vector<int> left(cur.begin(), cur.begin() + mid);
            vector<int> right(cur.begin() + mid, cur.end());

            auto qidx = buildExistQuery(pivot, left);
            long long res = ask(qidx);
            if (res > 0) cur = left;
            else cur = right;
        }
        int diff = cur[0];

        // Determine which one is '(' and which one is ')'
        long long res2 = ask(vector<int>{pivot, diff});
        int O, C; // indices of known '(' and ')'
        if (res2 == 1) {
            O = pivot;
            C = diff;
        } else {
            O = diff;
            C = pivot;
        }

        string ans(n, '?');
        ans[O - 1] = '(';
        ans[C - 1] = ')';

        // Weights w such that triangular numbers are superincreasing:
        // T(1)=1, T(2)=3, T(3)=6, T(5)=15, T(7)=28, T(10)=55, T(15)=120, T(21)=231,
        // T(30)=465, T(43)=946, T(62)=1953, T(88)=3916, T(125)=7875
        const vector<int> W = {1, 2, 3, 5, 7, 10, 15, 21, 30, 43, 62, 88, 125};

        // Collect unknown positions
        vector<int> unknown;
        unknown.reserve(n);
        for (int i = 1; i <= n; i++) {
            if (i == O || i == C) continue;
            unknown.push_back(i);
        }

        // Process unknowns in batches
        for (int ptr = 0; ptr < (int)unknown.size(); ) {
            int b = min((int)W.size(), (int)unknown.size() - ptr);
            vector<int> batch(unknown.begin() + ptr, unknown.begin() + ptr + b);
            ptr += b;

            vector<int> qidx;
            qidx.reserve(1000);
            for (int j = 0; j < b; j++) {
                int pos = batch[j];
                int w = W[j];

                for (int t = 0; t < w; t++) {
                    qidx.push_back(pos);
                    qidx.push_back(C);
                }
                qidx.push_back(C); // barrier
            }
            if ((int)qidx.size() > 1000) exit(0);

            long long val = ask(qidx);

            for (int j = b - 1; j >= 0; j--) {
                long long weight = tri(W[j]);
                int pos = batch[j];
                if (val >= weight) {
                    ans[pos - 1] = '(';
                    val -= weight;
                } else {
                    ans[pos - 1] = ')';
                }
            }
        }

        cout << "1 " << ans << '\n';
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        Solver s;
        s.n = n;
        s.solveCase();
    }
    return 0;
}