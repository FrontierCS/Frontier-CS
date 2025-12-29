#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    vector<char> firstResp(n);
    
    // First pass: reset and query all bakeries in order
    cout << "R" << endl;
    cout.flush();
    for (int i = 1; i <= n; ++i) {
        cout << "? " << i << endl;
        cout.flush();
        cin >> firstResp[i - 1];
    }
    
    // Count the number of 'N' responses
    int candidateCount = 0;
    for (char c : firstResp)
        if (c == 'N')
            ++candidateCount;
    
    // If k == n, the first pass gives the exact answer
    if (k == n) {
        cout << "! " << candidateCount << endl;
        return 0;
    }
    
    // For each position i that got 'N' and is beyond the first k,
    // check if it is a duplicate of the position i-k.
    // This handles duplicates that are exactly k apart.
    for (int i = k + 1; i <= n; ++i) {
        if (firstResp[i - 1] == 'N') {
            cout << "R" << endl;
            cout.flush();
            cout << "? " << i - k << endl;
            cout.flush();
            char tmp; cin >> tmp;
            cout << "? " << i << endl;
            cout.flush();
            char ans; cin >> ans;
            if (ans == 'Y') {
                --candidateCount;   // duplicate found
            }
        }
    }
    
    cout << "! " << candidateCount << endl;
    return 0;
}