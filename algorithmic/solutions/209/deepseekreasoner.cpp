#include <iostream>
#include <vector>
using namespace std;

int main() {
    int h;
    cin >> h;
    int n = (1 << h) - 1;
    long long total = 0;
    for (int u = 1; u <= n; ++u) {
        cout << "? " << u << " 1" << endl;
        long long resp;
        cin >> resp;
        total += resp;
    }
    cout << "! " << total << endl;
    return 0;
}