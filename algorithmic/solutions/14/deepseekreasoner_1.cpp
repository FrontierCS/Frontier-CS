#include <iostream>
#include <unordered_map>
#include <cmath>

using namespace std;

int main() {
    const long long m = 31623; // ceil(sqrt(1e9))
    unordered_map<long long, long long> baby; // vertex -> step index
    long long start, v;
    
    // Initial walk to learn starting vertex
    cout << "walk 0" << endl;
    cin >> start;
    baby[start] = 0;
    long long steps = 0;
    
    // Baby steps: walk 1 step at a time, record vertices
    for (long long i = 1; i < m; ++i) {
        cout << "walk 1" << endl;
        cin >> v;
        steps++;
        if (v == start) {
            // Found full cycle
            cout << "guess " << i << endl;
            return 0;
        }
        if (baby.find(v) != baby.end()) {
            // This case should not happen for n>i, but handle for safety
            long long n = i - baby[v];
            cout << "guess " << n << endl;
            return 0;
        }
        baby[v] = i;
    }
    
    // Now steps = m-1, we have m distinct vertices (including start)
    // Walk one more step to reach step m
    cout << "walk 1" << endl;
    cin >> v;
    steps++;
    if (baby.find(v) != baby.end()) {
        long long n = steps - baby[v];
        cout << "guess " << n << endl;
        return 0;
    }
    
    // Giant steps: walk m steps each time
    while (true) {
        cout << "walk " << m << endl;
        cin >> v;
        steps += m;
        if (baby.find(v) != baby.end()) {
            long long n = steps - baby[v];
            cout << "guess " << n << endl;
            return 0;
        }
    }
    
    return 0;
}