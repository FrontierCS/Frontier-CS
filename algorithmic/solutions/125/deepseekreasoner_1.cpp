#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

const int MAX = 90000; // 2*43000

int N;
bool paired[MAX];
vector<int> allIndices;

// Helper to toggle slice x and read response
int toggle(int x) {
    cout << "? " << x << endl;
    cout.flush();
    int r;
    cin >> r;
    return r;
}

// Insert all slices in v (assuming none are currently in the device)
// Returns the distinct count after inserting all.
int insertSet(const vector<int>& v) {
    int res = 0;
    for (int x : v) {
        res = toggle(x);
    }
    return res;
}

// Remove all slices in v (assuming all are currently in the device)
void removeSet(const vector<int>& v) {
    for (int x : v) {
        toggle(x);
    }
}

// Output a found pair and mark both slices as paired
void outputPair(int a, int b) {
    cout << "! " << a << " " << b << endl;
    cout.flush();
    paired[a] = paired[b] = true;
}

// Find the partner of slice a within set B using binary search.
// Assumes device is empty at start and leaves it empty.
int findPartner(int a, vector<int>& B) {
    int l = 0, r = (int)B.size() - 1;
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> range(B.begin() + l, B.begin() + mid + 1);
        int cnt = insertSet(range);          // insert range [l, mid]
        int r1 = toggle(a);                  // add a
        toggle(a);                           // remove a (ignore response)
        removeSet(range);                    // remove range
        if (r1 == cnt) {
            r = mid;                         // partner in left half
        } else {
            l = mid + 1;                     // partner in right half
        }
    }
    return B[l];
}

// Match all slices in A with their partners in B.
// Every a in A has its partner in B.
// Device must be empty at entry and will be empty at exit.
void match(vector<int> A, vector<int> B) {
    if (A.empty()) return;
    if (A.size() == 1 && B.size() == 1) {
        outputPair(A[0], B[0]);
        return;
    }
    if (A.size() == 1) {
        int p = findPartner(A[0], B);
        outputPair(A[0], p);
        return;
    }
    if (B.size() == 1) { // then A must have size 1 (handled above)
        return;
    }

    // Split B into two halves
    int m = B.size() / 2;
    vector<int> B1(B.begin(), B.begin() + m);
    vector<int> B2(B.begin() + m, B.end());

    // Insert B1 and get its distinct count
    int cntB1 = insertSet(B1);
    vector<int> A1, A2;
    for (int x : A) {
        int r = toggle(x);
        if (r == cntB1) A1.push_back(x);
        else            A2.push_back(x);
        toggle(x); // remove x
    }
    removeSet(B1); // remove B1

    // Recurse on the two subproblems
    match(A1, B1);
    match(A2, B2);
}

// Recursively find all pairs inside the set 'indices'.
// Device must be empty at entry and will be empty at exit.
void solve(vector<int> indices) {
    if (indices.size() == 2) {
        outputPair(indices[0], indices[1]);
        return;
    }
    if (indices.empty()) return;

    int mid = indices.size() / 2;
    vector<int> left(indices.begin(), indices.begin() + mid);
    vector<int> right(indices.begin() + mid, indices.end());

    // Insert the right half and get its distinct count
    int cntR = insertSet(right);

    // Classify each left slice: partner in right or not?
    vector<int> crossLeft, internalLeft;
    for (int x :