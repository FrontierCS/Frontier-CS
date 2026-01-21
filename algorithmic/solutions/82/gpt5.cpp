#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;

    auto ask = [&](int i, int j)->int{
        cout << "? " << i << " " << j << endl;
        cout.flush();
        int x; 
        if(!(cin >> x)) exit(0);
        if(x == -1) exit(0);
        return x;
    };

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, n);

    const int M = min(n-1, 12);
    const int MAX_TRIES = 3;

    int a = -1;
    vector<int> A; // OR(a, i)
    for (int attempt = 0; attempt < MAX_TRIES; ++attempt) {
        int cand = dist(rng);
        // prepare sample
        vector<int> sampleIdx;
        sampleIdx.reserve(M);
        vector<char> used(n+1, 0);
        used[cand] = 1;
        while ((int)sampleIdx.size() < M) {
            int x = dist(rng);
            if (!used[x]) {
                used[x] = 1;
                sampleIdx.push_back(x);
            }
        }
        vector<int> sampleVals(M);
        int minSample = INT_MAX;
        for (int i = 0; i < M; ++i) {
            int v = ask(cand, sampleIdx[i]);
            sampleVals[i] = v;
            minSample = min(minSample, v);
        }
        if (__builtin_popcount((unsigned)minSample) <= 7 || attempt == MAX_TRIES - 1) {
            // Accept this 'a'
            a = cand;
            A.assign(n+1, -1);
            // Fill known samples
            for (int i = 0; i < M; ++i) {
                A[sampleIdx[i]] = sampleVals[i];
            }
            break;
        }
    }

    // Compute A[i] = OR(a, i) for all i != a
    int pa = INT_MAX;
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        if (A.empty() || A[i] == -1) {
            int v = ask(a, i);
            if (!A.empty()) A[i] = v;
        }
        pa = min(pa, A[i]);
    }

    // Collect T = { i : A[i] == pa }
    vector<int> T;
    T.reserve(n);
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        if (A[i] == pa) T.push_back(i);
    }

    // Choose b not in T (preferably with maximal A[i])
    int b = -1;
    int maxA = -1;
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        if (A[i] > maxA) {
            maxA = A[i];
            b = i;
        }
    }

    // If all A[i] == pa (rare, a corresponds to n-1), pick any b != a
    if (b == -1 || maxA == pa) {
        for (int i = 1; i <= n; ++i) {
            if (i != a) { b = i; break; }
        }
    }

    // Ensure b not in T if possible
    bool bInT = false;
    if (!T.empty()) {
        for (int x : T) if (x == b) { bInT = true; break; }
        if (bInT) {
            // try to find another b not in T
            int bb = -1;
            for (int i = 1; i <= n; ++i) {
                if (i == a) continue;
                bool inT = false;
                for (int x : T) if (x == i) { inT = true; break; }
                if (!inT) { bb = i; break; }
            }
            if (bb != -1) { b = bb; bInT = false; }
        }
    }

    int z = -1;
    int minS = INT_MAX;

    if (!T.empty()) {
        // If b in T (can't query b with itself), pick b2 to use for the single conflicting index
        int b2 = -1;
        if (bInT) {
            for (int i = 1; i <= n; ++i) {
                if (i != a && i != b) { b2 = i; break; }
            }
            if (b2 == -1) {
                // n >= 3, but just in case
                for (int i = 1; i <= n; ++i) if (i != a) { b2 = i; break; }
            }
        }
        for (int x : T) {
            int v;
            if (bInT && x == b) {
                v = ask(b2, x);
            } else {
                v = ask(b, x);
            }
            int s = v & pa;
            if (s < minS) {
                minS = s;
                z = x;
            }
        }
    } else {
        // If T is empty (shouldn't happen), fall back: search zero by scanning all i with pair (a,b)
        for (int i = 1; i <= n; ++i) {
            if (i == a) continue;
            int v = ask(b, i);
            int s = (A[i] & v);
            if (s < minS) {
                minS = s;
                z = i;
            }
        }
    }

    // Now query with zero z to get all values
    vector<int> ans(n+1, 0);
    ans[z] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == z) continue;
        ans[i] = ask(z, i);
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}