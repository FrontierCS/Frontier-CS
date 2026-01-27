#include <bits/stdc++.h>
using namespace std;

long long ask(long long x, long long y) {
    cout << x << " " << y << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == 0) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    // Find min(a, b) using queries (m, m)
    long long low = 1, high = n + 1;
    while (high - low > 1) {
        long long mid = (low + high) / 2;
        long long res = ask(mid, mid);
        if (res == 3) high = mid;
        else low = mid; // res is 1 or 2 (or 0 -> handled in ask)
    }
    long long m0 = low;

    long long r = ask(m0, m0); // classify which equals m0, or 0
    if (r == 1) {
        // b = m0, find a
        long long L = m0 + 1, R = n;
        while (L <= R) {
            long long mid = (L + R) / 2;
            long long resp = ask(mid, m0);
            if (resp == 1) { // x < a
                L = mid + 1;
            } else if (resp == 3) { // x > a
                R = mid - 1;
            } else if (resp == 0) {
                exit(0);
            } else {
                // resp == 2 shouldn't happen when y == b
                // move safely to avoid infinite loop
                L = mid + 1;
            }
        }
    } else if (r == 2) {
        // a = m0, find b
        long long L = m0 + 1, R = n;
        while (L <= R) {
            long long mid = (L + R) / 2;
            long long resp = ask(m0, mid);
            if (resp == 2) { // y < b
                L = mid + 1;
            } else if (resp == 3) { // y > b
                R = mid - 1;
            } else if (resp == 0) {
                exit(0);
            } else {
                // resp == 1 shouldn't happen when x == a
                L = mid + 1;
            }
        }
    } else if (r == 0) {
        exit(0);
    } else {
        // Unexpected '3' here; try to adjust conservatively by binary searching 'a' and 'b' separately
        // Try to find 'a' with y fixed at 1 (may get ambiguous, but attempt)
        long long L = 1, R = n;
        while (L <= R) {
            long long mid = (L + R) / 2;
            long long resp = ask(mid, m0);
            if (resp == 1) L = mid + 1;
            else if (resp == 3) R = mid - 1;
            else if (resp == 0) exit(0);
            else L = mid + 1;
        }
        L = 1; R = n;
        while (L <= R) {
            long long mid = (L + R) / 2;
            long long resp = ask(m0, mid);
            if (resp == 2) L = mid + 1;
            else if (resp == 3) R = mid - 1;
            else if (resp == 0) exit(0);
            else L = mid + 1;
        }
    }

    return 0;
}