#include <bits/stdc++.h>
using namespace std;

static int n_global = 0;

static int ask(const vector<int>& xs) {
    cout << "?";
    for (int x : xs) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int p;
    if (!(cin >> p)) exit(0);
    if (p == -1) exit(0);
    return p;
}

static int findMaxAmong(const vector<int>& elems, int n) {
    vector<int> contenders = elems;

    int lastWinner = -1;
    vector<int> lastLosers;

    while ((int)contenders.size() > 1) {
        int sz = (int)contenders.size();
        if (sz >= n) {
            vector<int> race;
            race.reserve(n);
            for (int i = 0; i < n; i++) {
                race.push_back(contenders.back());
                contenders.pop_back();
            }

            int w = ask(race);
            lastWinner = w;
            lastLosers.clear();
            lastLosers.reserve(n - 1);
            for (int x : race) if (x != w) lastLosers.push_back(x);

            contenders.push_back(w);
        } else {
            int need = n - sz; // sz in [2..n-1]
            vector<int> race = contenders;
            for (int i = 0; i < need; i++) race.push_back(lastLosers[i]);
            int w = ask(race);
            return w;
        }
    }
    return contenders[0];
}

static void solveCase(int n) {
    int N = n * n;
    int K = N - n + 1;

    vector<int> rem;
    rem.reserve(N);
    vector<int> pos(N + 1, -1);
    for (int i = 1; i <= N; i++) {
        pos[i] = (int)rem.size();
        rem.push_back(i);
    }

    vector<int> ans;
    ans.reserve(K);

    for (int step = 0; step < K; step++) {
        int w = findMaxAmong(rem, n);
        ans.push_back(w);

        int idx = pos[w];
        int last = rem.back();
        rem[idx] = last;
        pos[last] = idx;
        rem.pop_back();
        pos[w] = -1;
    }

    cout << "!";
    for (int x : ans) cout << ' ' << x;
    cout << '\n';
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; tc++) {
        int n;
        cin >> n;
        if (!cin) return 0;
        if (n == -1) return 0;
        solveCase(n);
    }
    return 0;
}