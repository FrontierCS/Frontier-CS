#include <bits/stdc++.h>
using namespace std;

static int ask(int l, int r) {
    cout << "? " << l << " " << r << "\n";
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

static void answer(int pos) {
    cout << "! " << pos << "\n";
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        if (n == 2) {
            int q = ask(1, 2); // position of 1
            int posN = (q == 1 ? 2 : 1);
            answer(posN);
            continue;
        }

        int q = ask(1, n); // position of n-1

        bool maxLeft;
        if (q == 1) maxLeft = false;
        else if (q == n) maxLeft = true;
        else {
            int t = ask(1, q);
            maxLeft = (t == q);
        }

        int posN;
        if (maxLeft) {
            int l = 1, r = q - 1;
            while (l < r) {
                int mid = (l + r + 1) / 2;
                int t = ask(mid, q);
                if (t == q) l = mid;
                else r = mid - 1;
            }
            posN = l;
        } else {
            int l = q + 1, r = n;
            while (l < r) {
                int mid = (l + r) / 2;
                int t = ask(q, mid);
                if (t == q) r = mid;
                else l = mid + 1;
            }
            posN = l;
        }

        answer(posN);
    }
    return 0;
}