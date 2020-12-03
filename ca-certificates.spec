%define pkidir %{_sysconfdir}/pki
%define catrustdir %{_sysconfdir}/pki/ca-trust
%define classic_tls_bundle ca-bundle.crt
%define openssl_format_trust_bundle ca-bundle.trust.crt
%define p11_format_bundle ca-bundle.trust.p11-kit
%define legacy_default_bundle ca-bundle.legacy.default.crt
%define legacy_disable_bundle ca-bundle.legacy.disable.crt
%define java_bundle java/cacerts

Summary: The Mozilla CA root certificate bundle
Name: ca-certificates

# For the package version number, we use: year.{upstream version}
#
# The {upstream version} can be found as symbol
# NSS_BUILTINS_LIBRARY_VERSION in file nss/lib/ckfw/builtins/nssckbi.h
# which corresponds to the data in file nss/lib/ckfw/builtins/certdata.txt.
#
# The files should be taken from a released version of NSS, as published
# at https://ftp.mozilla.org/pub/mozilla.org/security/nss/releases/
#
# The versions that are used by the latest released version of 
# Mozilla Firefox should be available from:
# https://hg.mozilla.org/releases/mozilla-release/raw-file/default/security/nss/lib/ckfw/builtins/nssckbi.h
# https://hg.mozilla.org/releases/mozilla-release/raw-file/default/security/nss/lib/ckfw/builtins/certdata.txt
#
# The most recent development versions of the files can be found at
# http://hg.mozilla.org/projects/nss/raw-file/default/lib/ckfw/builtins/nssckbi.h
# http://hg.mozilla.org/projects/nss/raw-file/default/lib/ckfw/builtins/certdata.txt
# (but these files might have not yet been released).
#
# (until 2012.87 the version was based on the cvs revision ID of certdata.txt,
# but in 2013 the NSS projected was migrated to HG. Old version 2012.87 is 
# equivalent to new version 2012.1.93, which would break the requirement 
# to have increasing version numbers. However, the new scheme will work, 
# because all future versions will start with 2013 or larger.)

Version: 2020.2.44
# for Rawhide, please always use release >= 2
# for Fedora release branches, please use release < 2 (1.0, 1.1, ...)
Release: 1
License: Public Domain

Group: System Environment/Base
URL: https://fedoraproject.org/wiki/CA-Certificates

#Please always update both certdata.txt and nssckbi.h
Source0: certdata.txt
Source1: nssckbi.h
Source2: update-ca-trust
Source3: trust-fixes
Source4: certdata2pem.py
Source5: ca-legacy.conf
Source6: ca-legacy
Source9: ca-legacy.8.txt
Source10: update-ca-trust.8.txt
Source11: README.usr
Source12: README.etc
Source13: README.extr
Source14: README.java
Source15: README.openssl
Source16: README.pem
Source17: README.edk2
Source18: README.src

BuildArch: noarch

Requires(post): bash
Requires(post): grep
Requires(post): sed
Requires(post): coreutils
Requires: bash
Requires: grep
Requires: sed
Requires(post): p11-kit >= 0.23.10
Requires(post): p11-kit-trust >= 0.23.10
Requires: p11-kit >= 0.23.10
Requires: p11-kit-trust >= 0.23.10

BuildRequires: perl-interpreter
BuildRequires: python3
BuildRequires: openssl
BuildRequires: asciidoc
BuildRequires: libxslt

%description
This package contains the set of CA certificates chosen by the
Mozilla Foundation for use with the Internet PKI.

%prep
rm -rf %{name}
mkdir %{name}
mkdir %{name}/certs
mkdir %{name}/certs/legacy-default
mkdir %{name}/certs/legacy-disable
mkdir %{name}/java

%build
pushd %{name}/certs
 pwd
 cp %{SOURCE0} .
 python3 %{SOURCE4} >c2p.log 2>c2p.err
popd
pushd %{name}
 (
   cat <<EOF
# This is a bundle of X.509 certificates of public Certificate
# Authorities.  It was generated from the Mozilla root CA list.
# These certificates and trust/distrust attributes use the file format accepted
# by the p11-kit-trust module.
#
# Source: nss/lib/ckfw/builtins/certdata.txt
# Source: nss/lib/ckfw/builtins/nssckbi.h
#
# Generated from:
EOF
   cat %{SOURCE1}  |grep -w NSS_BUILTINS_LIBRARY_VERSION | awk '{print "# " $2 " " $3}';
   echo '#';
 ) > %{p11_format_bundle}

 touch %{legacy_default_bundle}
 NUM_LEGACY_DEFAULT=`find certs/legacy-default -type f | wc -l`
 if [ $NUM_LEGACY_DEFAULT -ne 0 ]; then
     for f in certs/legacy-default/*.crt; do 
       echo "processing $f"
       tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
       alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
       targs=""
       if [ -n "$tbits" ]; then
          for t in $tbits; do
             targs="${targs} -addtrust $t"
          done
       fi
       if [ -n "$targs" ]; then
          echo "legacy default flags $targs for $f" >> info.trust
          openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> %{legacy_default_bundle}
       fi
     done
 fi

 touch %{legacy_disable_bundle}
 NUM_LEGACY_DISABLE=`find certs/legacy-disable -type f | wc -l`
 if [ $NUM_LEGACY_DISABLE -ne 0 ]; then
     for f in certs/legacy-disable/*.crt; do 
       echo "processing $f"
       tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
       alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
       targs=""
       if [ -n "$tbits" ]; then
          for t in $tbits; do
             targs="${targs} -addtrust $t"
          done
       fi
       if [ -n "$targs" ]; then
          echo "legacy disable flags $targs for $f" >> info.trust
          openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> %{legacy_disable_bundle}
       fi
     done
 fi

 P11FILES=`find certs -name \*.tmp-p11-kit | wc -l`
 if [ $P11FILES -ne 0 ]; then
   for p in certs/*.tmp-p11-kit; do 
     cat "$p" >> %{p11_format_bundle}
   done
 fi
 # Append our trust fixes
 cat %{SOURCE3} >> %{p11_format_bundle}
popd

#manpage
cp %{SOURCE10} %{name}/update-ca-trust.8.txt
asciidoc.py -v -d manpage -b docbook %{name}/update-ca-trust.8.txt
xsltproc --nonet -o %{name}/update-ca-trust.8 /usr/share/asciidoc/docbook-xsl/manpage.xsl %{name}/update-ca-trust.8.xml

cp %{SOURCE9} %{name}/ca-legacy.8.txt
asciidoc.py -v -d manpage -b docbook %{name}/ca-legacy.8.txt
xsltproc --nonet -o %{name}/ca-legacy.8 /usr/share/asciidoc/docbook-xsl/manpage.xsl %{name}/ca-legacy.8.xml


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p -m 755 $RPM_BUILD_ROOT%{pkidir}/tls/certs
mkdir -p -m 755 $RPM_BUILD_ROOT%{pkidir}/java
mkdir -p -m 755 $RPM_BUILD_ROOT%{_sysconfdir}/ssl
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source/anchors
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source/blacklist
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/java
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/edk2
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/anchors
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/blacklist
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy
mkdir -p -m 755 $RPM_BUILD_ROOT%{_bindir}
mkdir -p -m 755 $RPM_BUILD_ROOT%{_mandir}/man8

install -p -m 644 %{name}/update-ca-trust.8 $RPM_BUILD_ROOT%{_mandir}/man8
install -p -m 644 %{name}/ca-legacy.8 $RPM_BUILD_ROOT%{_mandir}/man8
install -p -m 644 %{SOURCE11} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/README
install -p -m 644 %{SOURCE12} $RPM_BUILD_ROOT%{catrustdir}/README
install -p -m 644 %{SOURCE13} $RPM_BUILD_ROOT%{catrustdir}/extracted/README
install -p -m 644 %{SOURCE14} $RPM_BUILD_ROOT%{catrustdir}/extracted/java/README
install -p -m 644 %{SOURCE15} $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/README
install -p -m 644 %{SOURCE16} $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/README
install -p -m 644 %{SOURCE17} $RPM_BUILD_ROOT%{catrustdir}/extracted/edk2/README
install -p -m 644 %{SOURCE18} $RPM_BUILD_ROOT%{catrustdir}/source/README

install -p -m 644 %{name}/%{p11_format_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

install -p -m 644 %{name}/%{legacy_default_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
install -p -m 644 %{name}/%{legacy_disable_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}

install -p -m 644 %{SOURCE5} $RPM_BUILD_ROOT%{catrustdir}/ca-legacy.conf

touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}

# TODO: consider to dynamically create the update-ca-trust script from within
#       this .spec file, in order to have the output file+directory names at once place only.
install -p -m 755 %{SOURCE2} $RPM_BUILD_ROOT%{_bindir}/update-ca-trust

install -p -m 755 %{SOURCE6} $RPM_BUILD_ROOT%{_bindir}/ca-legacy

# touch ghosted files that will be extracted dynamically
# Set chmod 444 to use identical permission
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/tls-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/tls-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/email-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/email-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/objsign-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/objsign-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/%{java_bundle}
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/%{java_bundle}
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/edk2/cacerts.bin
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/edk2/cacerts.bin

# /etc/ssl/certs symlink for 3rd-party tools
ln -s ../pki/tls/certs \
    $RPM_BUILD_ROOT%{_sysconfdir}/ssl/certs
# legacy filenames
ln -s %{catrustdir}/extracted/pem/tls-ca-bundle.pem \
    $RPM_BUILD_ROOT%{pkidir}/tls/cert.pem
ln -s %{catrustdir}/extracted/pem/tls-ca-bundle.pem \
    $RPM_BUILD_ROOT%{pkidir}/tls/certs/%{classic_tls_bundle}
ln -s %{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle} \
    $RPM_BUILD_ROOT%{pkidir}/tls/certs/%{openssl_format_trust_bundle}
ln -s %{catrustdir}/extracted/%{java_bundle} \
    $RPM_BUILD_ROOT%{pkidir}/%{java_bundle}


%pre
if [ $1 -gt 1 ] ; then
  # Upgrade or Downgrade.
  # If the classic filename is a regular file, then we are upgrading
  # from an old package and we will move it to an .rpmsave backup file.
  # If the filename is a symbolic link, then we are good already.
  # If the system will later be downgraded to an old package with regular 
  # files, and afterwards updated again to a newer package with symlinks,
  # and the old .rpmsave backup file didn't get cleaned up,
  # then we don't backup again. We keep the older backup file.
  # In other words, if an .rpmsave file already exists, we don't overwrite it.
  #
  if ! test -e %{pkidir}/%{java_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/%{java_bundle}; then
      # a file exists
        if ! test -L %{pkidir}/%{java_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/%{java_bundle} %{pkidir}/%{java_bundle}.rpmsave
      fi
    fi
  fi

  if ! test -e %{pkidir}/tls/certs/%{classic_tls_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/tls/certs/%{classic_tls_bundle}; then
      # a file exists
      if ! test -L %{pkidir}/tls/certs/%{classic_tls_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/tls/certs/%{classic_tls_bundle} %{pkidir}/tls/certs/%{classic_tls_bundle}.rpmsave
      fi
    fi
  fi

  if ! test -e %{pkidir}/tls/certs/%{openssl_format_trust_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/tls/certs/%{openssl_format_trust_bundle}; then
      # a file exists
      if ! test -L %{pkidir}/tls/certs/%{openssl_format_trust_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/tls/certs/%{openssl_format_trust_bundle} %{pkidir}/tls/certs/%{openssl_format_trust_bundle}.rpmsave
      fi
    fi
  fi
fi


%post
#if [ $1 -gt 1 ] ; then
#  # when upgrading or downgrading
#fi
%{_bindir}/ca-legacy install
%{_bindir}/update-ca-trust


%files
%dir %{_sysconfdir}/ssl
%dir %{pkidir}/tls
%dir %{pkidir}/tls/certs
%dir %{pkidir}/java
%dir %{catrustdir}
%dir %{catrustdir}/source
%dir %{catrustdir}/source/anchors
%dir %{catrustdir}/source/blacklist
%dir %{catrustdir}/extracted
%dir %{catrustdir}/extracted/pem
%dir %{catrustdir}/extracted/openssl
%dir %{catrustdir}/extracted/java
%dir %{_datadir}/pki
%dir %{_datadir}/pki/ca-trust-source
%dir %{_datadir}/pki/ca-trust-source/anchors
%dir %{_datadir}/pki/ca-trust-source/blacklist
%dir %{_datadir}/pki/ca-trust-legacy

%config(noreplace) %{catrustdir}/ca-legacy.conf

%{_mandir}/man8/update-ca-trust.8.gz
%{_mandir}/man8/ca-legacy.8.gz
%{_datadir}/pki/ca-trust-source/README
%{catrustdir}/README
%{catrustdir}/extracted/README
%{catrustdir}/extracted/java/README
%{catrustdir}/extracted/openssl/README
%{catrustdir}/extracted/pem/README
%{catrustdir}/extracted/edk2/README
%{catrustdir}/source/README

# symlinks for old locations
%{pkidir}/tls/cert.pem
%{pkidir}/tls/certs/%{classic_tls_bundle}
%{pkidir}/tls/certs/%{openssl_format_trust_bundle}
%{pkidir}/%{java_bundle}
# symlink directory
%{_sysconfdir}/ssl/certs

# master bundle file with trust
%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}
# update/extract tool
%{_bindir}/update-ca-trust
%{_bindir}/ca-legacy
%ghost %{catrustdir}/source/ca-bundle.legacy.crt
# files extracted files
%ghost %{catrustdir}/extracted/pem/tls-ca-bundle.pem
%ghost %{catrustdir}/extracted/pem/email-ca-bundle.pem
%ghost %{catrustdir}/extracted/pem/objsign-ca-bundle.pem
%ghost %{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
%ghost %{catrustdir}/extracted/%{java_bundle}
%ghost %{catrustdir}/extracted/edk2/cacerts.bin


%changelog
* Wed Dec 2 2020 panxiaohe<panxiaoeh@huawei.com> - 2020.2.44-1
- Update to the the latest released version 2020.2.44

* Fri Aug 7 2020 huangzhenqiang<huangzhenqiang2@huawei.com> - 2020.2.42-1
- Update to the the latest released version 2020.2.42

* Mon Mar 9 2020 openEuler Buildteam <buildteam@openeuler.org> - 2020.2.40-1
- Update to the the latest released version 2020.2.40

* Mon Sep 23 2019 openEuler Buildteam <buildteam@openeuler.org> - 2019.2.36-1
- Update to the the latest released version 2.36

* Mon Sep 24 2018 Bob Relyea <rrelyea@redhat.com> - 2018.2.26-2
- Update to CKBI 2.26 from NSS 3.39

* Thu Jul 12 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2018.2.24-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Thu Jun 28 2018 Kai Engert <kaie@redhat.com> - 2018.2.24-5
- Ported scripts to python3

* Mon Jun 11 2018 Daiki Ueno <dueno@redhat.com> - 2018.2.24-4
- Extract certificate bundle in EDK2 format, suggested by Laszlo Ersek

* Mon Jun 04 2018 Kai Engert <kaie@redhat.com> - 2018.2.24-3
- Adjust ghost file permissions, rhbz#1564432

* Fri May 18 2018 Kai Engert <kaie@redhat.com> - 2018.2.24-2
- Update to CKBI 2.24 from NSS 3.37

* Wed Mar 14 2018 Iryna Shcherbina <ishcherb@redhat.com> - 2018.2.22-4
- Update Python 2 dependency declarations to new packaging standards
  (See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3)

* Fri Feb 23 2018 Patrick Uiterwijk <puiterwijk@redhat.com> - 2018.2.22-3
- Add post dep on coreutils for ln(1)

* Tue Feb 06 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-2
- Update to CKBI 2.22 from NSS 3.35

* Mon Jan 22 2018 Kai Engert <kaie@redhat.com> - 2017.2.20-6
- Depend on bash, grep, sed. Required for ca-legacy script execution.
- p11-kit is already required at %%post execution time. (rhbz#1537127)

* Fri Jan 19 2018 Kai Engert <kaie@redhat.com> - 2017.2.20-5
- Use the force, script! (Which sln did by default).

* Fri Jan 19 2018 Kai Engert <kaie@redhat.com> - 2017.2.20-4
- stop using sln in ca-legacy script.

* Fri Jan 19 2018 Kai Engert <kaie@redhat.com> - 2017.2.20-3
- Use ln -s, because sln was removed from glibc. rhbz#1536349

* Mon Nov 27 2017 Kai Engert <kaie@redhat.com> - 2017.2.20-2
- Update to CKBI 2.20 from NSS 3.34.1

* Tue Aug 15 2017 Kai Engert <kaie@redhat.com> - 2017.2.16-4
- Set P11_KIT_NO_USER_CONFIG=1 to prevent p11-kit from reading user
  configuration files (rhbz#1478172).

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2017.2.16-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Wed Jul 19 2017 Kai Engert <kaie@redhat.com> - 2017.2.16-2
- Update to (yet unreleased) CKBI 2.16 which is planned for NSS 3.32.
  Mozilla removed all trust bits for code signing.

* Wed Apr 26 2017 Kai Engert <kaie@redhat.com> - 2017.2.14-2
- Update to CKBI 2.14 from NSS 3.30.2

* Thu Feb 23 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-5
- For CAs trusted by Mozilla, set attribute nss-mozilla-ca-policy: true
- Set attribute modifiable: false
- Require p11-kit 0.23.4

* Mon Feb 13 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-4
- Changed the packaged bundle to use the flexible p11-kit-object-v1 file format,
  as a preparation to fix bugs in the interaction between p11-kit-trust and
  Mozilla applications, such as Firefox, Thunderbird etc.
- Changed update-ca-trust to add comments to extracted PEM format files.
- Added an utility to help with comparing output of the trust dump command.

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2017.2.11-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Jan 11 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-2
- Update to CKBI 2.11 from NSS 3.28.1

* Thu Sep 29 2016 Kai Engert <kaie@redhat.com> - 2016.2.10-2
- Update to CKBI 2.10 from NSS 3.27

* Tue Aug 16 2016 Kai Engert <kaie@redhat.com> - 2016.2.9-3
- Revert to the unmodified upstream CA list, changing the legacy trust
  to an empty list. Keeping the ca-legacy tool and existing config,
  however, the configuration has no effect after this change.

* Tue Aug 16 2016 Kai Engert <kaie@redhat.com> - 2016.2.9-2
- Update to CKBI 2.9 from NSS 3.26 with legacy modifications

* Fri Jul 15 2016 Kai Engert <kaie@redhat.com> - 2016.2.8-2
- Update to CKBI 2.8 from NSS 3.25 with legacy modifications

* Tue May 10 2016 Kai Engert <kaie@redhat.com> - 2016.2.7-5
- Only create backup files if there is an original file (bug 999017).

* Tue May 10 2016 Kai Engert <kaie@redhat.com> - 2016.2.7-4
- Use sln, not ln, to avoid the dependency on coreutils.

* Mon Apr 25 2016 Kai Engert <kaie@redhat.com> - 2016.2.7-3
- Fix typos in a manual page and in a README file.

* Wed Mar 16 2016 Kai Engert <kaie@redhat.com> - 2016.2.7-2
- Update to CKBI 2.7 from NSS 3.23 with legacy modifications

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2015.2.6-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Nov 23 2015 Kai Engert <kaie@redhat.com> - 2015.2.6-2
- Update to CKBI 2.6 from NSS 3.21 with legacy modifications

* Thu Aug 13 2015 Kai Engert <kaie@redhat.com> - 2015.2.5-2
- Update to CKBI 2.5 from NSS 3.19.3 with legacy modifications

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2015.2.4-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Tue May 05 2015 Kai Engert <kaie@redhat.com> - 2015.2.4-2
- Update to CKBI 2.4 from NSS 3.18.1 with legacy modifications

* Tue May 05 2015 Kai Engert <kaie@redhat.com> - 2015.2.3-4
- Fixed a typo in the ca-legacy manual page.

* Tue Mar 31 2015 Kai Engert <kaie@redhat.com> - 2015.2.3-3
- Don't use "enable" as a value for the legacy configuration, instead
  of the value "default", to make it clear that this preference isn't
  a promise to keep certificates enabled, but rather that we only
  keep them enabled as long as it's considered necessary.
- Changed the configuration file, the ca-legacy utility and filenames
  to use the term "default" (instead of the term "enable").
- Added a manual page for the ca-legacy utility.
- Fixed the ca-legacy utility to handle absence of the configuration
  setting and treat absence as the default setting.

* Fri Mar 20 2015 Kai Engert <kaie@redhat.com> - 2015.2.3-2
- Update to CKBI 2.3 from NSS 3.18 with legacy modifications
- Fixed a mistake in the legacy handling of the upstream 2.2 release:
  Removed two AOL certificates from the legacy group, because
  upstream didn't remove them as part of phasing out 1024-bit
  certificates, which means it isn't necessary to keep them.
- Fixed a mistake in the legacy handling of the upstream 2.1 release:
  Moved two NetLock certificates into the legacy group.

* Tue Dec 16 2014 Kai Engert <kaie@redhat.com> - 2014.2.2-2
- Update to CKBI 2.2 from NSS 3.17.3 with legacy modifications
- Update project URL
- Cleanup

* Sat Nov 15 2014 Peter Lemenkov <lemenkov@gmail.com> - 2014.2.1-7
- Restore Requires: coreutils

* Fri Nov 14 2014 Peter Lemenkov <lemenkov@gmail.com> - 2014.2.1-6
- A proper fix for rhbz#1158343

* Wed Oct 29 2014 Kai Engert <kaie@redhat.com> - 2014.2.1-5
- add Requires: coreutils (rhbz#1158343)

* Tue Oct 28 2014 Kai Engert <kaie@redhat.com> - 2014.2.1-4
- Introduce the ca-legacy utility and a ca-legacy.conf configuration file.
  By default, legacy roots required for OpenSSL/GnuTLS compatibility
  are kept enabled. Using the ca-legacy utility, the legacy roots can be
  disabled. If disabled, the system will use the trust set as provided
  by the upstream Mozilla CA list. (See also: rhbz#1158197)

* Sun Sep 21 2014 Kai Engert <kaie@redhat.com> - 2014.2.1-3
- Temporarily re-enable several legacy root CA certificates because of
  compatibility issues with software based on OpenSSL/GnuTLS,
  see rhbz#1144808

* Thu Aug 14 2014 Kai Engert <kaie@redhat.com> - 2014.2.1-2
- Update to CKBI 2.1 from NSS 3.16.4
- Fix rhbz#1130226

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2013.1.97-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed Mar 19 2014 Kai Engert <kaie@redhat.com> - 2013.1.97-2
- Update to CKBI 1.97 from NSS 3.16

* Mon Feb 10 2014 Kai Engert <kaie@redhat.com> - 2013.1.96-3
- Remove openjdk build dependency

* Sat Jan 25 2014 Ville Skyttä <ville.skytta@iki.fi> - 2013.1.96-2
- Own the %%{_datadir}/pki dir.

* Thu Jan 09 2014 Kai Engert <kaie@redhat.com> - 2013.1.96-1
- Update to CKBI 1.96 from NSS 3.15.4

* Tue Dec 17 2013 Kai Engert <kaie@redhat.com> - 2013.1.95-1
- Update to CKBI 1.95 from NSS 3.15.3.1

* Fri Sep 06 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-18
- Update the Entrust root stapled extension for compatibility with 
  p11-kit version 0.19.2, patch by Stef Walter, rhbz#988745

* Tue Sep 03 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-17
- merge manual improvement from f19

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2013.1.94-16
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 09 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-15
- clarification updates to manual page

* Mon Jul 08 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-14
- added a manual page and related build requirements
- simplify the README files now that we have a manual page
- set a certificate alias in trusted bundle (thanks to Ludwig Nussel)

* Mon May 27 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-13
- use correct command in README files, rhbz#961809

* Mon May 27 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-12
- update to version 1.94 provided by NSS 3.15 (beta)

* Mon Apr 22 2013 Kai Engert <kaie@redhat.com> - 2012.87-12
- Use both label and serial to identify cert during conversion, rhbz#927601
- Add myself as contributor to certdata2.pem.py and remove use of rcs/ident.
  (thanks to Michael Shuler for suggesting to do so)
- Update source URLs and comments, add source file for version information.

* Tue Mar 19 2013 Kai Engert <kaie@redhat.com> - 2012.87-11
- adjust to changed and new functionality provided by p11-kit 0.17.3
- updated READMEs to describe the new directory-specific treatment of files
- ship a new file that contains certificates with neutral trust
- ship a new file that contains distrust objects, and also staple a 
  basic constraint extension to one legacy root contained in the
  Mozilla CA list
- adjust the build script to dynamically produce most of above files
- add and own the anchors and blacklist subdirectories
- file generate-cacerts.pl is no longer required

* Fri Mar 08 2013 Kai Engert <kaie@redhat.com> - 2012.87-9
- Major rework for the Fedora SharedSystemCertificates feature.
- Only ship a PEM bundle file using the BEGIN TRUSTED CERTIFICATE file format.
- Require the p11-kit package that contains tools to automatically create
  other file format bundles.
- Convert old file locations to symbolic links that point to dynamically
  generated files.
- Old files, which might have been locally modified, will be saved in backup 
  files with .rpmsave extension.
- Added a update-ca-certificates script which can be used to regenerate
  the merged trusted output.
- Refer to the various README files that have been added for more detailed
  explanation of the new system.
- No longer require rsc for building.
- Add explanation for the future version numbering scheme,
  because the old numbering scheme was based on upstream using cvs,
  which is no longer true, and therefore can no longer be used.
- Includes changes from rhbz#873369.

* Thu Mar 07 2013 Kai Engert <kaie@redhat.com> - 2012.87-2.fc19.1
- Ship trust bundle file in /usr/share/pki/ca-trust-source/, temporarily in addition.
  This location will soon become the only place containing this file.

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2012.87-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Jan 04 2013 Paul Wouters <pwouters@redhat.com> - 2012.87-1
- Updated to r1.87 to blacklist mis-issued turktrust CA certs

* Wed Oct 24 2012 Paul Wouters <pwouters@redhat.com> - 2012.86-2
- Updated blacklist with 20 entries (Diginotar, Trustwave, Comodo(?)
- Fix to certdata2pem.py to also check for CKT_NSS_NOT_TRUSTED 

* Tue Oct 23 2012 Paul Wouters <pwouters@redhat.com> - 2012.86-1
- update to r1.86

* Mon Jul 23 2012 Joe Orton <jorton@redhat.com> - 2012.85-2
- add openssl to BuildRequires

* Mon Jul 23 2012 Joe Orton <jorton@redhat.com> - 2012.85-1
- update to r1.85

* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2012.81-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Feb 13 2012 Joe Orton <jorton@redhat.com> - 2012.81-1
- update to r1.81

* Thu Jan 12 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2011.80-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Nov  9 2011 Joe Orton <jorton@redhat.com> - 2011.80-1
- update to r1.80
- fix handling of certs with dublicate Subject names (#733032)

* Thu Sep  1 2011 Joe Orton <jorton@redhat.com> - 2011.78-1
- update to r1.78, removing trust from DigiNotar root (#734679)

* Wed Aug  3 2011 Joe Orton <jorton@redhat.com> - 2011.75-1
- update to r1.75

* Wed Apr 20 2011 Joe Orton <jorton@redhat.com> - 2011.74-1
- update to r1.74

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2011.70-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Wed Jan 12 2011 Joe Orton <jorton@redhat.com> - 2011.70-1
- update to r1.70

* Tue Nov  9 2010 Joe Orton <jorton@redhat.com> - 2010.65-3
- update to r1.65

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-3
- package /etc/ssl/certs symlink for third-party apps (#572725)

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-2
- rebuild

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-1
- update to certdata.txt r1.63
- use upstream RCS version in Version

* Fri Mar 19 2010 Joe Orton <jorton@redhat.com> - 2010-4
- fix ca-bundle.crt (#575111)

* Thu Mar 18 2010 Joe Orton <jorton@redhat.com> - 2010-3
- update to certdata.txt r1.58
- add /etc/pki/tls/certs/ca-bundle.trust.crt using 'TRUSTED CERTICATE' format
- exclude ECC certs from the Java cacerts database
- catch keytool failures
- fail parsing certdata.txt on finding untrusted but not blacklisted cert

* Fri Jan 15 2010 Joe Orton <jorton@redhat.com> - 2010-2
- fix Java cacert database generation: use Subject rather than Issuer
  for alias name; add diagnostics; fix some alias names.

* Mon Jan 11 2010 Joe Orton <jorton@redhat.com> - 2010-1
- adopt Python certdata.txt parsing script from Debian

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2009-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jul 22 2009 Joe Orton <jorton@redhat.com> 2009-1
- update to certdata.txt r1.53

* Mon Feb 23 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2008-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Tue Oct 14 2008 Joe Orton <jorton@redhat.com> 2008-7
- update to certdata.txt r1.49

* Wed Jun 25 2008 Thomas Fitzsimmons <fitzsim@redhat.com> - 2008-6
- Change generate-cacerts.pl to produce pretty aliases.

* Mon Jun  2 2008 Joe Orton <jorton@redhat.com> 2008-5
- include /etc/pki/tls/cert.pem symlink to ca-bundle.crt

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-4
- use package name for temp dir, recreate it in prep

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-3
- fix source script perms
- mark packaged files as config(noreplace)

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-2
- add (but don't use) mkcabundle.pl
- tweak description
- use /usr/bin/keytool directly; BR java-openjdk

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-1
- Initial build (#448497)
