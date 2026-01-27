#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int t;
    cin >> t;

    while (t--) {
        int n;
        cin >> n;

        int a = 1;
        int impostor = -1;

        for (int i = 2; i <= n; ++i) {
            cout << "? " << a << " " << i << endl;
            int ans1;
            cin >> ans1;
            cout << "? " << i << " " << a << endl;
            int ans2;
            cin >> ans2;

            if (ans1 != ans2) {
                // impostor is either a or i
                int c = 1;
                while (c == a || c == i) ++c;
                cout << "? " << a << " " << c << endl;
                int ansA;
                cin >> ansA;
                cout << "? " << i << " " << c << endl;
                int ansB;
                cin >> ansB;

                if (ansA != ansB) {
                    impostor = i;
                } else {
                    impostor = a;
                }
                break;
            }
        }

        if (impostor == -1) {
            impostor = a;
        }

        cout << "! " << impostor << endl;
    }

    return 0;
}