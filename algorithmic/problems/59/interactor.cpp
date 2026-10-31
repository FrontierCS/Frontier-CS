#include <cmath>
#include <algorithm>

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int n = inf.readInt(1, 30000, "n");
    // Seed the generator from a per-test secret in the answer file so the
    // hidden array is not a fixed function of the default rng seed (#208).
    rnd.setSeed(ans.readLong());
    cout << n << endl;
    cout.flush();

    // === ���ɷ������������ ===
    vector<int> a(n);
    iota(a.begin(), a.end(), 1);
    for (int i = 0; i < n; i++) {
        int l = i;
        int r = min(n - 1, i + 2);
        int j = rnd.next(l, r); // pick j uniformly in [i, min(n-1, i+2)]
        swap(a[i], a[j]);
    }

    const int limit = n * 5 / 3 + 5;
    int queries = 0;

    while (true) {
    	string cmd;
        try {
            cmd = ouf.readWord();  // ? �ĳ� readWord()
        } catch (...) {
            quitf(_fail, "Unexpected EOF or invalid token while reading command.");
        }

        if (cmd == "?") {
            ++queries;
            if (queries > limit) {
                quitf(_wa, "Too many queries (%d > %d)", queries, limit);
            }

            int i = ouf.readInt(1, n, "i");
            int j = ouf.readInt(1, n, "j");
            if (i == j)
                quitf(_wa, "Queried identical indices (%d == %d)", i, j);

            if (a[i - 1] < a[j - 1])
                cout << "<" << endl;
            else
                cout << ">" << endl;
            cout.flush();
        }
        else if (cmd == "!") {
			vector<int> b(n);
			for (int i = 0; i < n; ++i)
			    b[i] = ouf.readInt(1, n, "a[i]");
            set<int> s(b.begin(), b.end());
            if ((int)s.size() != n)
                quitf(_wa, "Array is not a permutation.");

            if (b != a)
                quitf(_wa, "Wrong final array.");

            // The hard query budget is the executable 60-point reference.
            // Correctness and the query limit were checked above.
            const double score = queries == 0 ? 100.0
                : (double)min(100.0L, 60.0L + log((long double)limit)
                                                   - log((long double)queries));
            const double ratio = score / 100.0;
            const double ratio_unbounded = ratio;
            const double score_unbounded = score;

            string msg = format(
                "Correct! Queries = %d (limit = %d). Ratio: %.12f (Score: %.2f). RatioUnbounded: %.12f (ScoreUnbounded: %.2f)",
                queries, limit, ratio, score, ratio_unbounded, score_unbounded);

            quitp(ratio, msg.c_str());
        }
        else {
            quitf(_wa, "Unexpected command: %s", cmd.c_str());
        }
    }
}

