#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> alive(n);
    iota(alive.begin(), alive.end(), 1);

    vector<char> lastMatch(n + 1, 1);
    vector<char> inQ(n + 1, 0);

    auto ask = [&](const vector<int>& S) -> string {
        cout << "? " << (int)S.size();
        for (int v : S) cout << " " << v;
        cout << endl;
        cout.flush();
        string reply;
        if (!(cin >> reply)) exit(0);
        return reply;
    };

    auto guess = [&](int g) -> bool {
        cout << "! " << g << endl;
        cout.flush();
        string reply;
        if (!(cin >> reply)) exit(0);
        return reply.size() >= 2 && reply[0] == ':' && reply[1] == ')';
    };

    int questions = 0;

    while ((int)alive.size() > 2) {
        vector<int> S;

        if (questions == 0) {
            // First query: split approximately in half
            int k = (int)alive.size() / 2;
            if (k == 0) k = 1;
            // Optional shuffle for fairness
            // shuffle(alive.begin(), alive.end(), rng);
            for (int i = 0; i < k; ++i) S.push_back(alive[i]);
        } else {
            // Split both groups approximately in half
            vector<int> g0, g1;
            g0.reserve(alive.size());
            g1.reserve(alive.size());
            for (int v : alive) {
                if (lastMatch[v] == 0) g0.push_back(v);
                else g1.push_back(v);
            }
            // Optional shuffle for fairness
            // shuffle(g0.begin(), g0.end(), rng);
            // shuffle(g1.begin(), g1.end(), rng);
            int k0 = (int)g0.size() / 2;
            int k1 = (int)g1.size() / 2;
            for (int i = 0; i < k0; ++i) S.push_back(g0[i]);
            for (int i = 0; i < k1; ++i) S.push_back(g1[i]);
            if (S.empty()) {
                // Ensure non-empty query
                S.push_back(alive[rng() % alive.size()]);
            }
        }

        for (int v : S) inQ[v] = 1;

        string reply = ask(S);
        bool yes = (reply.size() && (reply[0] == 'Y' || reply[0] == 'y'));

        vector<int> newAlive;
        newAlive.reserve(alive.size());

        if (questions == 0) {
            for (int v : alive) {
                bool nowMatch = (inQ[v] ? yes : !yes);
                lastMatch[v] = nowMatch;
                newAlive.push_back(v);
            }
        } else {
            for (int v : alive) {
                bool nowMatch = (inQ[v] ? yes : !yes);
                if (!(lastMatch[v] == 0 && nowMatch == 0)) {
                    lastMatch[v] = nowMatch;
                    newAlive.push_back(v);
                }
            }
        }

        for (int v : S) inQ[v] = 0;

        alive.swap(newAlive);
        questions++;

        if ((int)alive.size() <= 2) break;
    }

    if (alive.empty()) {
        // Should not happen under problem constraints; fallback safe guess
        cout << "! 1" << endl;
        cout.flush();
        return 0;
    } else if ((int)alive.size() == 1) {
        guess(alive[0]);
        return 0;
    } else {
        if (guess(alive[0])) return 0;
        guess(alive[1]);
        return 0;
    }
}