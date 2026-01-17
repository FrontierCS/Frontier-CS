#include <iostream>
#include <vector>

using namespace std;

// Returns true if a[i] < a[j]
bool query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char res;
    cin >> res;
    return res == '<';
}

int main() {
    // Interactive problem, strict synchronization is usually required but cin/cout with endl is safe.
    // Standard optimization can be used but keep flush in mind.
    ios_base::sync_with_stdio(false);
    
    int n;
    if (!(cin >> n)) return 0;

    // The stack 's' will maintain indices such that a[s[0]] < a[s[1]] < ... < a[s.back()]
    // This is effectively maintaining the sorted order of the prefix processed so far.
    // Given the constraint a_i <= i+2, the number of inversions (and thus pops) is limited.
    vector<int> s;
    s.reserve(n);

    for (int i = 1; i <= n; ++i) {
        vector<int> buffer;
        // We need to insert i into the sorted sequence s.
        // We compare i with the top of the stack. 
        // If a[i] < a[top], then top is greater than i, so we pop it to buffer.
        // We repeat until a[i] > a[top] or stack is empty.
        while (!s.empty()) {
            int top = s.back();
            if (query(i, top)) { // a[i] < a[top]
                s.pop_back();
                buffer.push_back(top);
            } else {
                break;
            }
        }
        s.push_back(i);
        // Restore the popped elements. They are already sorted relative to each other 
        // and all are greater than a[i].
        while (!buffer.empty()) {
            s.push_back(buffer.back());
            buffer.pop_back();
        }
    }

    // Now s contains indices sorted by their values.
    // Since the values are a permutation of 1..n, the k-th element in s corresponds to value k+1.
    // i.e., a[s[k]] = k + 1
    vector<int> a(n + 1);
    for (int k = 0; k < n; ++k) {
        a[s[k]] = k + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;

    return 0;
}