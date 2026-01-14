#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    int N;
    cin >> N;
    string S(N, '0');
    const int M = 1002;
    for (int i = 0; i < N; ++i) {
        vector<int> a(M), b(M);
        // normal increment states for steps before i
        for (int j = 0; j < i; ++j) {
            a[j] = j + 1;
            b[j] = j + 1;
        }
        // special transition at step i
        a[i] = 1000;
        b[i] = 1001;
        // sink states for the rest
        for (int j = i + 1; j < 1000; ++j) {
            a[j] = 1000;
            b[j] = 1000;
        }
        a[1000] = 1000; b[1000] = 1000;
        a[1001] = 1000; b[1001] = 1000;
        // output query
        cout << "1 " << M;
        for (int j = 0; j < M; ++j) cout << " " << a[j];
        for (int j = 0; j < M; ++j) cout << " " << b[j];
        cout << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == 1000) S[i] = '0';
        else if (res == 1001) S[i] = '1';
    }
    cout << "0 " << S << endl;
    return 0;
}