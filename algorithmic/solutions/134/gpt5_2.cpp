#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if(!(cin >> n)) {
        return 0;
    }

    auto ask = [&](long long x, long long y)->int{
        x = max(1LL, min(x, n));
        y = max(1LL, min(y, n));
        cout << x << " " << y << "\n";
        cout.flush();
        int r;
        if(!(cin >> r)) exit(0);
        if(r == 0) exit(0);
        return r;
    };

    long long A = 1, B = 1;

    // Bitwise probing with fallbacks
    for(long long s = 1LL<<60; s > 0; s >>= 1) {
        bool canA = (A + s <= n);
        bool canB = (B + s <= n);
        if(canA && canB) {
            int r = ask(A + s, B + s);
            if(r == 1) {
                A += s;
            } else if(r == 2) {
                B += s;
            } else { // r == 3
                // Try to disambiguate
                int r2 = ask(A + s, B);
                if(r2 == 1) {
                    A += s;
                } else {
                    int r3 = ask(A, B + s);
                    if(r3 == 2) B += s;
                }
            }
        } else if(canA) {
            int r = ask(A + s, B);
            if(r == 1) A += s;
        } else if(canB) {
            int r = ask(A, B + s);
            if(r == 2) B += s;
        }
    }

    // Final confirmation / adjustments
    while(true) {
        int r = ask(A, B);
        if(r == 0) break;
        if(r == 1 && A < n) {
            // try to push A up using small steps
            long long lo = A+1, hi = n, best = A;
            while(lo <= hi) {
                long long mid = (lo + hi) >> 1;
                int rr = ask(mid, B);
                if(rr == 1) {
                    best = mid;
                    lo = mid + 1;
                } else if(rr == 3) {
                    hi = mid - 1;
                } else if(rr == 2) {
                    if(B < n) {
                        int tmp = ask(A, B+1);
                        if(tmp == 2) B++;
                    } else hi = mid - 1;
                } else break;
            }
            A = max(A, best);
        } else if(r == 2 && B < n) {
            long long lo = B+1, hi = n, best = B;
            while(lo <= hi) {
                long long mid = (lo + hi) >> 1;
                int rr = ask(A, mid);
                if(rr == 2) {
                    best = mid;
                    lo = mid + 1;
                } else if(rr == 3) {
                    hi = mid - 1;
                } else if(rr == 1) {
                    if(A < n) {
                        int tmp = ask(A+1, B);
                        if(tmp == 1) A++;
                    } else hi = mid - 1;
                } else break;
            }
            B = max(B, best);
        } else if(r == 3) {
            // Try adjust both towards bounds
            if(A < n) {
                int rr = ask(A+1, B);
                if(rr == 1) A++;
            }
            if(B < n) {
                int rr = ask(A, B+1);
                if(rr == 2) B++;
            }
        } else {
            break;
        }
    }

    return 0;
}