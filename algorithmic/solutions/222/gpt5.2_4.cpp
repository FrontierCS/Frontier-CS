#include <bits/stdc++.h>
using namespace std;

static int ask(int v, long long x) {
    cout << "? " << v << " " << x << "\n";
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return (int)res;
}

static void answer(long long s) {
    cout << "! " << s << "\n";
    cout.flush();
    int verdict;
    if (!(cin >> verdict)) exit(0);
    if (verdict == -1) exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int M = 1000; // M^2 = 1e6 (max cycle length bound)

    for (int tc = 0; tc < n; tc++) {
        int c = ask(1, 1); // guaranteed to be on the cycle

        vector<int> nodes(M + 1);
        unordered_map<int, int> pos;
        pos.reserve(M * 2);
        pos.max_load_factor(0.7f);

        nodes[0] = c;
        pos[c] = 0;

        int cur = c;
        int s_small = -1;

        for (int i = 1; i <= M; i++) {
            cur = ask(cur, 1);
            nodes[i] = cur;
            if (cur == c) {
                s_small = i;
                break;
            }
            if (i < M) pos[cur] = i;
        }

        if (s_small != -1) {
            answer(s_small);
            continue;
        }

        long long s = -1;
        for (int k = 1; k <= M; k++) {
            int v = ask(c, 1LL * k * M);
            auto it = pos.find(v);
            if (it != pos.end()) {
                s = 1LL * k * M - it->second;
                break;
            }
        }

        if (s == -1) s = 1000000; // should never happen with valid interaction
        answer(s);
    }

    return 0;
}