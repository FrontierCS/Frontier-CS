#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using i128 = __int128_t;

static inline i128 floor_div(i128 a, i128 b) { // b > 0
    if (a >= 0) return a / b;
    return - ( (-a + b - 1) / b );
}

static inline long long clamp_ll(long long x, long long lo, long long hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int MAXQ = 53;

    vector<ull> W0(MAXQ + 1), W1(MAXQ + 1);
    W0[0] = 1;
    W1[0] = 1;
    for (int r = 1; r <= MAXQ; r++) {
        W1[r] = W0[r - 1];
        W0[r] = W0[r - 1] + W1[r - 1];
    }

    vector<int> P0(n), P1;
    iota(P0.begin(), P0.end(), 1);

    vector<int> vis(n + 1, 0);
    int timer = 0;

    auto ask = [&](const vector<int>& S) -> string {
        cout << "? " << (int)S.size();
        for (int v : S) cout << ' ' << v;
        cout << '\n';
        cout.flush();
        string ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    auto guess = [&](int g) -> string {
        cout << "! " << g << '\n';
        cout.flush();
        string res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    int asked = 0;

    while (asked < MAXQ && (int)(P0.size() + P1.size()) > 2) {
        int r = MAXQ - asked;
        ull w0 = W0[r - 1];
        ull w1 = W1[r - 1];
        ull delta0 = w0 - w1;

        long long p0 = (long long)P0.size();
        long long p1 = (long long)P1.size();

        i128 total = (i128)(p0 + p1) * (i128)w0 + (i128)p0 * (i128)w1;
        i128 target = total / 2;
        i128 base = (i128)p0 * (i128)w1;

        long long approxY1 = 0;
        if (w0 != 0) approxY1 = (long long)floor_div(target - base, (i128)w0);

        const int WINDOW = 300;
        vector<long long> y1cands;
        y1cands.reserve(2 * WINDOW + 10);
        y1cands.push_back(0);
        y1cands.push_back(p1);
        for (int d = -WINDOW; d <= WINDOW; d++) {
            long long y = approxY1 + d;
            y = clamp_ll(y, 0LL, p1);
            y1cands.push_back(y);
        }
        sort(y1cands.begin(), y1cands.end());
        y1cands.erase(unique(y1cands.begin(), y1cands.end()), y1cands.end());

        i128 bestCost = -1;
        long long bestY0 = 0, bestY1 = 0;

        auto eval = [&](long long y0, long long y1v) {
            i128 yes = base + (i128)y1v * (i128)w0 + (i128)y0 * (i128)delta0;
            i128 no = total - yes;
            i128 cost = (yes > no) ? yes : no;
            if (bestCost < 0 || cost < bestCost) {
                bestCost = cost;
                bestY0 = y0;
                bestY1 = y1v;
            }
        };

        for (long long y1v : y1cands) {
            if (delta0 == 0) {
                eval(0, y1v);
                eval(p0, y1v);
                continue;
            }
            i128 rem = target - (base + (i128)y1v * (i128)w0);
            i128 f = floor_div(rem, (i128)delta0);
            long long cand0 = (long long)f;
            for (long long t : {cand0 - 2, cand0 - 1, cand0, cand0 + 1, cand0 + 2, 0LL, p0}) {
                long long y0 = clamp_ll(t, 0LL, p0);
                eval(y0, y1v);
            }
        }

        vector<int> S;
        S.reserve((size_t)(bestY0 + bestY1));
        for (long long i = 0; i < bestY0; i++) S.push_back(P0[(size_t)i]);
        for (long long i = 0; i < bestY1; i++) S.push_back(P1[(size_t)i]);

        if (S.empty()) {
            if (!P0.empty()) S.push_back(P0[0]);
            else if (!P1.empty()) S.push_back(P1[0]);
            else break;
        }

        timer++;
        for (int v : S) vis[v] = timer;

        string ans = ask(S);

        vector<int> nP0, nP1;
        nP0.reserve(P0.size() + P1.size());
        nP1.reserve(P0.size());

        if (ans == "YES") {
            for (int x : P0) {
                if (vis[x] == timer) nP0.push_back(x);
                else nP1.push_back(x);
            }
            for (int x : P1) {
                if (vis[x] == timer) nP0.push_back(x);
            }
        } else { // "NO"
            for (int x : P0) {
                if (vis[x] == timer) nP1.push_back(x);
                else nP0.push_back(x);
            }
            for (int x : P1) {
                if (vis[x] != timer) nP0.push_back(x);
            }
        }

        P0.swap(nP0);
        P1.swap(nP1);

        asked++;
    }

    vector<int> candidates;
    candidates.reserve(P0.size() + P1.size());
    for (int x : P0) candidates.push_back(x);
    for (int x : P1) candidates.push_back(x);

    if (candidates.empty()) return 0;

    if ((int)candidates.size() == 1) {
        guess(candidates[0]);
        return 0;
    }

    // Up to 2 guesses
    string r1 = guess(candidates[0]);
    if (r1 == ":)") return 0;
    guess(candidates[1]);
    return 0;
}