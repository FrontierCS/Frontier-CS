#include <bits/stdc++.h>
using namespace std;

static const int M = 1000;

long long ask(long long v, unsigned long long x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    return res;
}

void answer(long long s) {
    cout << "! " << s << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    for (int tc = 0; tc < n; ++tc) {
        long long b = ask(1, 1);

        unordered_map<long long, int> mp;
        mp.reserve(2048);
        mp.max_load_factor(0.7);

        mp[b] = 0;
        long long best = (1LL<<62);

        // Baby steps i = 1..M-1
        for (int i = 1; i < M; ++i) {
            long long val = ask(b, i);
            auto it = mp.find(val);
            if (it != mp.end()) {
                long long diff = i - it->second;
                if (diff > 0 && diff < best) best = diff;
            } else {
                mp[val] = i;
            }
        }

        // Giant steps j = 1..M
        for (int j = 1; j <= M; ++j) {
            long long val = ask(b, 1LL * j * M);
            auto it = mp.find(val);
            if (it != mp.end()) {
                long long diff = 1LL * j * M - it->second;
                if (diff > 0 && diff < best) best = diff;
            }
        }

        if (best == (1LL<<62)) best = 1; // Fallback, should not happen per problem constraints
        answer(best);

        long long verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }

    return 0;
}