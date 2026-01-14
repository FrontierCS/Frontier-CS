#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int N;
    cin >> N;
    string S(N, '0');
    for (int i = 0; i < N; ++i) {
        int m = i + 2;
        vector<int> a(m), b(m);
        for (int x = 0; x < i; ++x) {
            a[x] = x + 1;
            b[x] = x + 1;
        }
        a[i] = i;
        b[i] = i + 1;
        if (i + 1 < m) {
            a[i + 1] = i +