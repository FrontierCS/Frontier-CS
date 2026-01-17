#include <iostream>
#include <vector>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<int> spf(n + 1);
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            if ((long long)i * i <= n) {
                for (int j = i * i; j <= n; j += i) {
                    if (spf[j] == 0) spf[j] = i;
                }
            }
        }
    }
    
    vector<int> f(n + 1);
    f[1] = 1;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) { // i is prime
            if (i == 2) {
                f[i] = -1;
            } else {
                int r = i % 8;
                if (r == 1 || r == 7) f[i] = 1;
                else f[i] = -1; // r == 3 or 5
            }
        } else {
            f[i] = f[spf[i]] * f[i / spf[i]];
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        cout << f[i] << (i < n ? ' ' : '\n');
    }
    
    return 0;
}