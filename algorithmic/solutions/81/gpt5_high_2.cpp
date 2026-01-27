#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    auto ask = [&](const vector<int>& a, const vector<int>& b) -> int {
        int m = (int)a.size();
        cout << 1 << " " << m << "\n";
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << a[i];
        }
        cout << "\n";
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << b[i];
        }
        cout << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x < 0) exit(0);
        return x;
    };

    string ans(N, '0');

    // Retrieve pairs of bits (i, i+1) for i = 0, 2, 4, ...
    for (int p = 0; p + 1 < N; p += 2) {
        // Use cycle of length N on states [0..N-1], plus 1 extra state as internal node
        int m = max(N + 1, 4); // ensure at least 4 distinct states for leaves
        vector<int> a(m, 0), b(m, 0);

        // Base cycle on first N states: move to next modulo N regardless of bit
        for (int s = 0; s < N; ++s) {
            a[s] = (s + 1) % N;
            b[s] = (s + 1) % N;
        }
        // Default transitions for extra states (not used unless targeted)
        for (int s = N; s < m; ++s) {
            a[s] = 0;
            b[s] = 0;
        }

        int s0 = p;        // position p
        int s1 = p + 1;    // position p+1

        // Leaves must be within [0..N-1] to ensure proper advancement over remaining steps
        // Since N = 1000 in the problem, this holds.
        int c0 = 0, c1 = 1, c2 = 2, c3 = 3;

        // One extra internal node for the second branch
        int A = N; // index of extra node (exists since m >= N+1 or 4)
        a[s0] = s1;  // if S[p] == 0 -> go to s1
        b[s0] = A;   // if S[p] == 1 -> go to A

        // At next step p+1, branch to leaves based on S[p+1]
        a[s1] = c0;  // 00 -> c0
        b[s1] = c1;  // 01 -> c1

        a[A] = c2;   // 10 -> c2
        b[A] = c3;   // 11 -> c3

        int r = ask(a, b);

        // Number of remaining steps after position p+1
        int R = N - 1 - s1;
        int c = r - R;
        c %= N;
        if (c < 0) c += N;

        if (c == c0) {
            ans[s0] = '0'; ans[s1] = '0';
        } else if (c == c1) {
            ans[s0] = '0'; ans[s1] = '1';
        } else if (c == c2) {
            ans[s0] = '1'; ans[s1] = '0';
        } else if (c == c3) {
            ans[s0] = '1'; ans[s1] = '1';
        } else {
            // Fallback (should not happen for valid interactor)
            ans[s0] = '0'; ans[s1] = '0';
        }
    }

    // If N is odd, retrieve the last single bit at position N-1
    if (N % 2 == 1) {
        int p = N - 1;
        int m;
        vector<int> a, b;
        if (N >= 2) {
            m = N;
            a.assign(m, 0);
            b.assign(m, 0);
            for (int s = 0; s < N; ++s) {
                a[s] = (s + 1) % N;
                b[s] = (s + 1) % N;
            }
            a[p] = 0; // if S[p] == 0 -> go to 0
            b[p] = 1; // if S[p] == 1 -> go to 1
            int r = ask(a, b);
            int R = N - 1 - p; // 0
            int c = r - R;
            c %= N; if (c < 0) c += N;
            if (c == 0) ans[p] = '0';
            else if (c == 1) ans[p] = '1';
            else ans[p] = '0';
        } else {
            // N == 1
            m = 2;
            a.assign(m, 0);
            b.assign(m, 0);
            a[0] = 0; b[0] = 1;
            a[1] = 0; b[1] = 1;
            int r = ask(a, b);
            ans[0] = (r == 0 ? '0' : '1');
        }
    }

    cout << 0 << " " << ans << "\n";
    cout.flush();
    return 0;
}