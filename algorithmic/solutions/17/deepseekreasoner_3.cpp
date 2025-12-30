#include <iostream>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        int s = ask(1, n);
        int m;
        if (s == 1) {
            int low = 2, high = n;
            while (low < high) {
                int mid = (low + high) / 2;
                int res = ask(1, mid);
                if (res == s) high = mid;
                else low = mid + 1;
            }
            m = low;
        } else if (s == n) {
            int low = 1, high = n - 1;
            while (low < high) {
                int mid = (low + high + 1) / 2;
                int res = ask(mid, n);
                if (res == s) low = mid;
                else high = mid - 1;
            }
            m = low;
        } else {
            int t = ask(1, s);
            if (t == s) {
                int low = 1, high = s - 1;
                while (low < high) {
                    int mid = (low + high + 1) / 2;
                    int res = ask(mid, n);
                    if (res == s) low = mid;
                    else high = mid - 1;
                }
                m = low;
            } else {
                int low = s + 1, high = n;
                while (low < high) {
                    int mid = (low + high) / 2;
                    int res = ask(1, mid);
                    if (res == s) high = mid;
                    else low = mid + 1;
                }
                m = low;
            }
        }
        cout << "! " << m << endl;
    }
    return 0;
}