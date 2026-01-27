#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct InteractiveSolver {
    int ask(int i, int j) {
        cout << "? " << i << " " << j << "\n" << flush;
        int x;
        if (!(cin >> x)) die();
        if (x == -1) die();
        return x;
    }

    int b(int i, int j) { // 1 iff exactly one of {i,j} is the impostor
        int a1 = ask(i, j);
        int a2 = ask(j, i);
        return a1 ^ a2;
    }

    void answer(int x) {
        cout << "! " << x << "\n" << flush;
    }

    void solve_case(int n) {
        if (n == 3) {
            int b12 = b(1, 2);
            if (b12 == 0) {
                answer(3);
                return;
            }
            int b13 = b(1, 3);
            answer(b13 == 1 ? 1 : 2);
            return;
        }

        int b12 = b(1, 2);
        if (b12 == 1) {
            int b13 = b(1, 3);
            answer(b13 == 1 ? 1 : 2);
            return;
        }

        // b12 == 0 => players 1 and 2 are guaranteed NOT impostor.
        int good = 1;

        int imp = -1;
        for (int i = 3; i + 1 <= n; i += 2) {
            int bij = b(i, i + 1);
            if (bij == 1) {
                int bgi = b(good, i);
                imp = (bgi == 1 ? i : i + 1);
                break;
            }
        }
        if (imp == -1) {
            // Only possible when n is odd: the last unpaired player is the impostor.
            imp = n;
        }
        answer(imp);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    InteractiveSolver solver;
    while (t--) {
        int n;
        cin >> n;
        solver.solve_case(n);
    }
    return 0;
}