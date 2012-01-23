#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Mon 07 Nov 2011 17:55:05 CET 

"""Generates face-verification-like performance tables that can be fed to
performance computation scripts. Two tables are always generated: development
and test.
"""

import sys
import os
import argparse
import bob
import re

CLIENT_RE = re.compile(r'client(?P<n>\d{3})')

def is_attack(filename):
  return filename.find('attack') != -1

def extract_client_no(filename):
  """Extracts the client number from a file"""
  return int(CLIENT_RE.search(os.path.basename(filename)).group(0).replace('client',''))

def write_file(clients, stems, config, frames, thourough, filename):
  """Writes a 4-column file with the data from the stems given"""

  outfile = open(filename, 'w')

  for client_id in clients:

    client_no = extract_client_no(client_id) #this will work!
    score_dir = os.path.join(config.scores_dir, client_id)
    dirs = [k for k in os.listdir(score_dir) if int(k) <= frames]

    for key, stem in stems.iteritems(): #all samples
      data = []

      claimed_id = extract_client_no(stem)

      if is_attack(stem) and claimed_id != client_no:
        #skip attacks to different identities.
        continue

      if not thourough and claimed_id != client_no:
        #skip real-accesses to different identities.
        continue

      if is_attack(stem): claimed_id = 'attack'

      for d in dirs:
        fname = os.path.join(config.scores_dir, client_id, d, stem + '.hdf5')
        if not os.path.exists(fname):
          print "WARNING: Ignoring unexisting file %s" % (fname)
          continue
        data.append(bob.io.load(fname)[0,0])
      if len(data) == 0: 
        average = 0.0
      else:
        average = sum(data)/len(data) #average score for this match
      outfile.write('%s %s %s %.5e\n' % (client_no, claimed_id, stem, average))

def main():

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('-c', '--config-file', metavar='FILE', type=str,
      dest='config_file', default="", help='Filename of the configuration file to use to run the script on the grid (defaults to "%(default)s")')
  parser.add_argument('-p', '--protocol', metavar='PROTOCOL', type=str,
      dest='protocol', default='', help='The name of the protocol to use when evaluating the performance of the data on face verification (defaults to "%(default)s)". If you do *not* specify a protocol, just run the baseline face verification.')
  parser.add_argument('-t', '--thourough', default=False,
      dest='thourough', action='store_true', help='If set will be thourough for client/impostor scores concerning real-accesses (not attacks) while comparing the client model')
  parser.add_argument('-f', '--frames', metavar='INT', type=int,
      dest='frames', default=10, help='Number of frames to average the scores from')
  parser.add_argument('-i', '--input-dir', metavar='DIR', type=str,
      dest='idir', default='/idiap/temp/aanjos/spoofing/verif/scores',
      help='Name of the directory containing the scores organized in this way: <client-name>/<frame-number>/rcd...')
  args = parser.parse_args()

  # An adjustment
  if not args.protocol: args.thourough = True

  # Loads the configuration
  import imp 
  config = imp.load_source('config', args.config_file)

  # Database
  db = bob.db.replay.Database()

  # Finds the files that belong to the negative and positive samples of each
  # of the experiment groups: devel, test
  print "Querying database for model names...",
  sys.stdout.flush()
  client_dict = db.files(cls='enroll', groups=('devel'))
  dev_client = set()
  for key, value in client_dict.iteritems():
    client_id = value.split('_')[0].split('/')[1]
    dev_client.add(client_id)
  dev_client = sorted(list(dev_client))
  client_dict = db.files(cls='enroll', groups=('test'))
  test_client = set()
  for key, value in client_dict.iteritems():
    client_id = value.split('_')[0].split('/')[1]
    test_client.add(client_id)
  test_client = sorted(list(test_client))
  print "%d development;" % len(dev_client),
  print "%d test" % len(test_client)

  # Finds all files for real access
  print "Querying database for real/devel files...",
  sys.stdout.flush()
  if not args.protocol:
    dev_real_dict = db.files(cls='real', groups=('devel'))
  else:
    dev_real_dict = db.files(cls=('real', 'attack'), groups=('devel'),
        protocol=args.protocol)
  print "%d files" % (len(dev_real_dict))

  print "Querying database for real/test files...",
  sys.stdout.flush()
  if not args.protocol:
    test_real_dict = db.files(cls='real', groups=('test'))
  else:
    test_real_dict = db.files(cls=('real', 'attack'), groups=('test'),
        protocol=args.protocol)
  print "%d files" % (len(test_real_dict))

  # Runs the whole shebang for writing an output file
  write_file(dev_client, dev_real_dict, config, args.frames,
      args.thourough, 'devel.4c')
  write_file(test_client, test_real_dict, config, args.frames, 
      args.thourough, 'test.4c')

if __name__ == '__main__':
  main()
