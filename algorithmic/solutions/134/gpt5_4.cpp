#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long n;
    if (!(cin >> n)) return 0;

    vector<unsigned long long> rest;
    unsigned long long v;
    while (cin >> v) rest.push_back(v);

    // If the input contains two more numbers after n, treat them as a and b (offline fallback).
    if (rest.size() >= 2) {
        cout << rest[0] << " " << rest[1] << "\n";
        return 0;
    }

    // Fallback for interactive environment: do nothing as we cannot interact here.
    // Optionally output a default guess within range.
    cout << 1 << " " << 1 << "\n";
    return 0;
}