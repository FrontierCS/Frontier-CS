#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<char> assign(n + 1, 0), bestAssign(n + 1, 0);
    int bestS = -1;

    auto computeSatisfied = [&](const vector<char>& asg) {
        int s = 0;
        for (int i = 0; i < m; ++i) {
            bool sat = false;
            for (int k = 0; k < 3; ++k) {
                int lit = clauses[i][k];
                int v = lit > 0 ? lit : -lit;
                if (lit > 0) {
                    if (asg[v]) { sat = true; break; }
                } else {
                    if (!asg[v]) { sat = true; break; }
                }
            }
            if (sat) ++s;
        }
        return s;
    };

    const int TOTAL_STEPS = 2000;
    const int MAX_RESTARTS = 10;
    int stepsPerRestart = (m == 0 ? 0 : max(1, TOTAL_STEPS / MAX_RESTARTS));

    vector<int> delta(n + 1);

    for (int restart = 0; restart < MAX_RESTARTS; ++restart) {
        // Random initial assignment
        for (int i = 1; i <= n; ++i) {
            assign[i] = rng() & 1;
        }

        int currentS = computeSatisfied(assign);
        if (currentS > bestS) {
            bestS = currentS;
            bestAssign = assign;
            if (bestS == m) break;
        }

        for (int step = 0; step < stepsPerRestart; ++step) {
            if (currentS == m) break;

            fill(delta.begin(), delta.end(), 0);

            for (int i = 0; i < m; ++i) {
                int l0 = clauses[i][0];
                int l1 = clauses[i][1];
                int l2 = clauses[i][2];

                int v0 = l0 > 0 ? l0 : -l0;
                int v1 = l1 > 0 ? l1 : -l1;
                int v2 = l2 > 0 ? l2 : -l2;

                bool t0 = (l0 > 0) ? (assign[v0] != 0) : (assign[v0] == 0);
                bool t1 = (l1 > 0) ? (assign[v1] != 0) : (assign[v1] == 0);
                bool t2 = (l2 > 0) ? (assign[v2] != 0) : (assign[v2] == 0);

                int tCount = (int)t0 + (int)t1 + (int)t2;

                if (tCount == 0) {
                    ++delta[v0];
                    ++delta[v1];
                    ++delta[v2];
                } else if (tCount == 1) {
                    if (t0) --delta[v0];
                    else if (t1) --delta[v1];
                    else --delta[v2];
                }
            }

            int bestDelta = INT_MIN;
            int bestVar = -1;
            for (int v = 1; v <= n; ++v) {
                if (delta[v] > bestDelta) {
                    bestDelta = delta[v];
                    bestVar = v;
                }
            }

            if (bestVar == -1 || bestDelta <= 0) break;

            assign[bestVar] ^= 1;
            currentS += bestDelta;

            if (currentS > bestS) {
                bestS = currentS;
                bestAssign = assign;
                if (bestS == m) break;
            }
        }

        if (bestS == m) break;
    }

    // If no restart improved bestS (possible when m == 0), ensure bestAssign is defined
    if (bestS < 0) {
        for (int i = 1; i <= n; ++i) bestAssign[i] = 0;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(bestAssign[i]);
    }
    cout << '\n';

    return 0;
}