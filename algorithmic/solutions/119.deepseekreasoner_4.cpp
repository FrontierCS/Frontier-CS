#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

typedef long long ll;

const ll MOD = 1000000007;
const ll X = 100;   // chosen constant
const ll Y = 100;   // chosen constant

int main() {
    int n;
    cin >> n;
    
    if (n == 1) {
        // special case: only one operator
        vector<ll> q(2);
        q[0] = Y;
        q[1] = X;
        cout << "? " << q[0] << " " << q[1] << endl;
        ll R;
        cin >> R;
        ll val_plus = (X + Y - 1) % MOD;
        ll val_mul = (X * Y) % MOD;
        ll A_plus = (R - val_plus + MOD) % MOD;
        ll A_mul = (R - val_mul + MOD) % MOD;
        int op1;
        if (0 <= A_plus && A_plus <= n) {
            op1 = 0; // '+'
        } else {
            op1 = 1; // '*'
        }
        cout << "! " << op1 << endl;
        return 0;
    }
    
    // n >= 2
    // Determine first operator and total additions A
    vector<ll> q(n+1, 1);
    q[0] = Y;
    q[1] = X;
    cout << "?";
    for (ll v : q) cout << " " << v;
    cout << endl;
    ll R;
    cin >> R;
    ll val_plus = (X + Y - 1) % MOD;
    ll val_mul = (X * Y) % MOD;
    ll A_plus = (R - val_plus + MOD) % MOD;
    ll A_mul = (R - val_mul + MOD) % MOD;
    int op1;
    ll A;
    if (0 <= A_plus && A_plus <= n) {
        op1 = 0;
        A = A_plus;
    } else {
        op1 = 1;
        A = A_mul;
    }
    
    vector<int> ops(n);
    ops[0] = op1;
    int k1 = (op1 == 0 ? 1 : 0); // number of additions before next position
    
    // Determine operators 2 to n-1
    for (int i = 2; i <= n-1; i++) {
        if (k1 > 0) {
            q.assign(n+1, 1);
            q[0] = 1;
            q[i] = X; // a_i = X for operator i
            cout << "?";
            for (ll v : q) cout << " " << v;
            cout << endl;
            cin >> R;
            ll R_add = (X + A) % MOD;
            ll R_mul = (X + A + k1 * (X - 1)) % MOD;
            if (R == R_add) {
                ops[i-1] = 0;
                k1++;
            } else {
                ops[i-1] = 1;
            }
        } else {
            q.assign(n+1, 1);
            q[0] = Y;
            q[i] = X;
            cout << "?";
            for (ll v : q) cout << " " << v;
            cout << endl;
            cin >> R;
            ll R_add = (X + Y + A - 1) % MOD;
            ll R_mul = (X * Y + A) % MOD;
            if (R == R_add) {
                ops[i-1] = 0;
                k1 = 1;
            } else {
                ops[i-1] = 1;
            }
        }
    }
    
    // Determine last operator (index n-1)
    if (A == k1) {
        ops[n-1] = 1;
    } else if (A == k1 + 1) {
        ops[n-1] = 0;
    } else {
        // fallback: should not happen, but guess
        if (A > k1) ops[n-1] = 0;
        else ops[n-1] = 1;
    }
    
    cout << "!";
    for (int i = 0; i < n; i++) cout << " " << ops[i];
    cout << endl;
    
    return 0;
}