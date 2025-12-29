#include <bits/stdc++.h>
using namespace std;

static int n;
static int L, R;

static pair<int,int> ask_excluding(int a, int b) {
    vector<int> idx;
    idx.reserve(n - 2);
    for (int i = 1; i <= n; i++) {
        if (i == a || i == b) continue;
        idx.push_back(i);
    }

    cout << "0 " << (n - 2);
    for (int x : idx) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int m1, m2;
    if (!(cin >> m1 >> m2)) exit(0);
    if (m1 < 0 || m2 < 0) exit(0);
    return {m1, m2};
}

static void answer(int i, int j) {
    cout << "1 " << i << ' ' << j << '\n';
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    L = n / 2;
    R = L + 1;

    int base = 1;
    int x = -1, y = -1;

    // First pass: try to find either the median pair directly, or a mixed (lower,upper) pair (response == (L,R)).
    for (int j = 2; j <= n; j++) {
        auto res = ask_excluding(base, j);
        if (res.first == L - 1 && res.second == R + 1) {
            // Excluding (L,R) yields (L-1, R+1) uniquely.
            answer(base, j);
        }
        if (res.first == L && res.second == R) {
            x = base;
            y = j;
            break;
        }
    }

    // If no mixed pair found, base must be one of the medians; find the other by scanning.
    if (x == -1) {
        for (int j = 2; j <= n; j++) {
            auto res = ask_excluding(base, j);
            if (res.first == L - 1 && res.second == R + 1) {
                answer(base, j);
            }
        }
        exit(0);
    }

    // Now (x,y) is a mixed pair: one is lower (<L), the other is upper (>R), neither is a median.
    // Probe with x to find which median it links to.
    int idxL = -1, idxR = -1;
    bool xIsUpper = false, xIsLower = false;

    for (int i = 1; i <= n; i++) {
        if (i == x) continue;
        auto res = ask_excluding(x, i);
        if (res.first == L - 1 && res.second == R) { // missing {L, upper}
            idxL = i;
            xIsUpper = true;
            break;
        }
        if (res.first == L && res.second == R + 1) { // missing {R, lower}
            idxR = i;
            xIsLower = true;
            break;
        }
    }

    if (!xIsUpper && !xIsLower) exit(0);

    int U = -1, D = -1;
    if (xIsUpper) {
        U = x;
        D = y;
    } else {
        D = x;
        U = y;
    }

    if (idxL == -1) {
        // Find L using the known upper index U
        for (int i = 1; i <= n; i++) {
            if (i == U) continue;
            auto res = ask_excluding(U, i);
            if (res.first == L - 1 && res.second == R) {
                idxL = i;
                break;
            }
        }
    }

    if (idxR == -1) {
        // Find R using the known lower index D
        for (int i = 1; i <= n; i++) {
            if (i == D) continue;
            auto res = ask_excluding(D, i);
            if (res.first == L && res.second == R + 1) {
                idxR = i;
                break;
            }
        }
    }

    if (idxL == -1 || idxR == -1) exit(0);
    answer(idxL, idxR);
    return 0;
}