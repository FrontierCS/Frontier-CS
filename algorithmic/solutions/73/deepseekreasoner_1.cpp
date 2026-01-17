#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> cnt(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            cout << "0 " << i << " " << j << endl;
            int res;
            cin >> res;
            if (res == 1) {
                cnt[i]++;
            } else {
                cnt[j]++;
            }
        }
    }
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        p[i] = cnt[i] + 1;
    }
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    return 0;
}