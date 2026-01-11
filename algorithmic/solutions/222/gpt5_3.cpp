#include <bits/stdc++.h>
using namespace std;

static const long long MAXV = 1000000;
static const int B = 1000;
static const int K = (int)((MAXV + B - 1) / B);

long long ask(long long v, long long x) {
    cout << "? " << v << " " << x << endl << flush;
    long long y;
    if (!(cin >> y)) exit(0);
    if (y == -1) exit(0);
    return y;
}

void answer(long long s) {
    cout << "! " << s << endl << flush;
}

long long reduce_to_s(long long c, long long M) {
    long long s = M;
    for (long long p = 2; p * p <= s; ++p) {
        if (s % p == 0) {
            while (s % p == 0) {
                long long t = s / p;
                long long y = ask(c, t);
                if (y == c) s = t;
                else break;
            }
        }
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    for (int tc = 0; tc < n; ++tc) {
        // Get a cycle vertex
        long long c = ask(1, 1);
        
        // Map from node id to smallest j in [0, B-1] such that ?c j = id.
        // Using unordered_map to avoid initializing a 1e6 array per test.
        unordered_map<int,int> pos;
        pos.reserve(B * 2);
        pos.max_load_factor(0.7f);
        pos[(int)c] = 0; // j = 0 corresponds to c itself (no query needed)
        
        long long M = -1;
        // Baby steps: j = 1..B-1
        for (int j = 1; j < B; ++j) {
            long long y = ask(c, j);
            if (y == c) { // Found a multiple of s <= B-1
                M = j;
                break;
            }
            int yi = (int)y;
            auto it = pos.find(yi);
            if (it == pos.end() || j < it->second) pos[yi] = j;
        }
        
        // Giant steps if not found
        if (M == -1) {
            for (int k = 1; k <= K; ++k) {
                long long y = ask(c, 1LL * k * B);
                int yi = (int)y;
                auto it = pos.find(yi);
                if (it != pos.end()) {
                    M = 1LL * k * B - it->second;
                    break;
                }
            }
        }
        
        // Reduce M to s by dividing out prime factors
        long long s = reduce_to_s(c, M);
        
        answer(s);
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}