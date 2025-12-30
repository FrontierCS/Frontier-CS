#include <iostream>
#include <vector>
#include <cmath>
using namespace std;

int main() {
    long long n;
    cin >> n;
    if (n == 1) {
        cout << "1\n1";
        return 0;
    }
    int k = 0;
    long long p = 1;
    while (p <= n) {
        k++;
        p <<= 1;
    }
    cout << k << "\n";
    for (int i = 0; i < k; i++) {
        if (i > 0) cout << " ";
        cout << (1LL << i);
    }
    return 0;
}