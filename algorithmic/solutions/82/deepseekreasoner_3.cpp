#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    random_device rd;
    mt19937 g(rd());
    shuffle(order.begin(), order.end(), g);

    int a = order[0];
    int b = order[1];

    vector<tuple<int, int, int, int, int>> history;
    history.reserve(n - 2);

    for (int idx = 2; idx < n; ++idx) {
        int i = order[idx];
        cout << "? " << a << " " << i << endl;
        int val_a;
        cin >> val_a;
        if (val_a == -1) return 0;
        cout << "? " << b << " " << i << endl;
        int val_b;
        cin >> val_b;
        if (val_b == -1) return 0;

        history.emplace_back(i, a, b, val_a, val_b);

        if (val_a < val_b) {
            b = i;
        } else if (val_a > val_b) {
            a = i;
        }
    }

    int zero = -1;
    for (auto &[i, a_old, b_old, val_a, val_b] : history) {
        if (val_a != val_b) {
            zero = (val_a < val_b) ? a_old : b_old;
            break;
        }
    }

    if (zero == -1) {
        cout << "? " << a << " " << b << endl;
        int v;
        cin >> v;
        if (v == -1) return 0;
        for (int idx = 0; idx < n; ++idx) {
            int c = order[idx];
            if (c == a || c == b) continue;
            cout << "? " << a << " " << c << endl;
            int ac;
            cin >> ac;
            if (ac == -1) return 0;
            cout << "? " << b << " " << c << endl;
            int bc;
            cin >> bc;
            if (bc == -1) return 0;
            if (ac != bc) {
                zero = (ac < bc) ? a : b;
                break;
            }
        }
        if (zero == -1) zero = a;
    }

    vector<int> p(n + 1, -1);
    p[zero] = 0;

    for (auto &[i, a_old, b_old, val_a, val_b] : history) {
        if (a_old == zero) {
            p[i] = val_a;
        } else if (b_old == zero) {
            p[i] = val_b;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (p[i] == -1) {
            cout << "? " << zero << " " << i << endl;
            int val;
            cin >> val;
            if (val == -1) return 0;
            p[i] = val;
        }
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << " ";
    }
    cout << endl;

    return 0;
}