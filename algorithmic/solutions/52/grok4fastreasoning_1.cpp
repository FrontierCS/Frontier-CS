#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, l1, l2;
    cin >> n >> l1 >> l2;
    srand(time(NULL));
    for (int i = n; i > 1; i--) {
        int j = 1 + rand() % i;
        if (j != i) {
            cout << 2 << " " << i << " " << j << endl;
            cout.flush();
            int conf;
            cin >> conf;
        }
    }
    int k = 1;
    while (k < n) {
        int test_slot = k + 1;
        int candidate = k + 2;
        bool found = false;
        while (!found) {
            cout << 1 << " " << k << " " << test_slot << endl;
            cout.flush();
            int x;
            cin >> x;
            if (x == 1) {
                found = true;
                k++;
            } else {
                if (candidate > n) {
                    assert(false);
                }
                cout << 2 << " " << test_slot << " " << candidate << endl;
                cout.flush();
                int conf;
                cin >> conf;
                candidate++;
            }
        }
    }
    cout << 3;
    for (int i = 1; i <= n; i++) cout << " " << i;
    cout << endl;
    cout.flush();
    return 0;
}