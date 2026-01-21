#include <bits/stdc++.h>
using namespace std;

static int n, m, N;
static int queries = 0;
static const int QUERY_LIMIT = 30000;

static bool readInt(int &x) {
    if (!(cin >> x)) return false;
    return true;
}

static int ask(int ring, int dir) {
    cout << "? " << ring << " " << dir << "\n";
    cout.flush();
    int a;
    if (!readInt(a)) exit(0);
    if (a == -1) exit(0);
    ++queries;
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!readInt(n)) return 0;
    readInt(m);
    N = n * m;

    // Initialize current display value by doing a rotation and undoing it.
    int t = ask(0, +1);
    (void)t;
    int cur = ask(0, -1);

    const int target = N - m;

    vector<int> dir(n, +1);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    int stagnationRounds = 0;

    while (queries + 2 <= QUERY_LIMIT && cur < target) {
        shuffle(order.begin(), order.end(), rng);

        bool improvedThisRound = false;
        int startCur = cur;

        for (int idx = 0; idx < n && queries + 2 <= QUERY_LIMIT && cur < target; ++idx) {
            int i = order[idx];
            int d = dir[i];

            int nxt = ask(i, d);
            if (nxt >= cur) {
                improvedThisRound |= (nxt > cur);
                cur = nxt;
                // Keep direction as is.
            } else {
                // Revert, flip direction preference.
                int back = ask(i, -d);
                cur = back;
                dir[i] = -d;
            }
        }

        if (cur > startCur) improvedThisRound = true;

        if (!improvedThisRound) {
            ++stagnationRounds;
            // Plateau exploration: random non-decreasing moves, avoid excessive reverts.
            int tries = min(5 * n, 500);
            for (int it = 0; it < tries && queries + 2 <= QUERY_LIMIT && cur < target; ++it) {
                int i = (int)(rng() % n);
                int d = (rng() & 1) ? dir[i] : -dir[i];

                int nxt = ask(i, d);
                if (nxt >= cur) {
                    cur = nxt;
                    dir[i] = d;
                    if (nxt > startCur) improvedThisRound = true;
                } else {
                    int back = ask(i, -d);
                    cur = back;
                }
            }

            // Occasionally allow a small worsening move to escape strict local maxima, then continue.
            if (cur < target && queries + 2 <= QUERY_LIMIT && stagnationRounds % 3 == 0) {
                int i = (int)(rng() % n);
                int d = (rng() & 1) ? +1 : -1;
                int nxt = ask(i, d);
                // Keep it even if it worsens, but try a quick recovery with a few greedy steps on same ring.
                cur = nxt;
                dir[i] = d;
                for (int k = 0; k < 2 * m && queries + 2 <= QUERY_LIMIT && cur < target; ++k) {
                    int nn = ask(i, dir[i]);
                    if (nn >= cur) {
                        cur = nn;
                    } else {
                        int back = ask(i, -dir[i]);
                        cur = back;
                        dir[i] = -dir[i];
                        break;
                    }
                }
            }
        } else {
            stagnationRounds = 0;
        }
    }

    cout << "!";
    for (int i = 1; i < n; ++i) cout << " " << 0;
    cout << "\n";
    cout.flush();
    return 0;
}