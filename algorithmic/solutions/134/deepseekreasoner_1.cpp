#include <iostream>
#include <cstdlib>
using namespace std;

typedef long long ll;

int main() {
    ll n;
    cin >> n;

    // Phase 1: find a
    ll low_a = 1, high_a = n;
    ll y_a = 1;
    while (low_a < high_a) {
        ll x = (low_a + high_a) / 2;
        while (true) {
            cout << x << " " << y_a << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == 0) {
                return 0;
            } else if (res == 1) {
                low_a = x + 1;
                break;
            } else if (res == 2) {
                // double y_a, but cap at n
                if (y_a <= n / 2) {
                    y_a *= 2;
                } else {
                    y_a = n;
                }
                // continue with the same x
            } else if (res == 3) {
                high_a = x - 1;
                break;
            }
        }
    }
    ll a = low_a;

    // Phase 2: find b using known a
    // y_a is an upper bound for b (since we doubled until no response 2)
    ll low_b = 1, high_b = y_a;
    while (low_b < high_b) {
        ll y = (low_b + high_b) / 2;
        cout << a << " " << y << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == 0) {
            return 0;
        } else if (res == 2) {
            low_b = y + 1;
        } else { // res == 3 (response 1 cannot occur because x = a)
            high_b = y - 1;
        }
    }
    ll b = low_b;

    // Final confirmation (should return 0)
    cout << a << " " << b << endl;
    cout.flush();
    int res;
    cin >> res;
    // res should be 0
    return 0;
}